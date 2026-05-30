# app/core/rag_pipeline.py
# Core RAG pipeline: query routing → retrieval → grounded generation

import os
import json
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from app.core.vectorstore import rbac_retriever
from app.core.rbac import UserContext

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Source routing keywords — helps prioritise which silos to search
SOURCE_ROUTING_HINTS = {
    "finance_reports": ["revenue", "budget", "profit", "loss", "financial", "expense", "forecast", "quarter", "fiscal"],
    "hr_records": ["employee", "salary", "leave", "performance", "hire", "onboarding", "headcount", "benefits", "payroll"],
    "engineering_docs": ["api", "architecture", "deployment", "service", "infrastructure", "bug", "release", "system", "database"],
    "legal_contracts": ["contract", "agreement", "clause", "liability", "compliance", "regulation", "gdpr", "audit", "policy"],
    "sales_data": ["deal", "pipeline", "opportunity", "customer", "crm", "quota", "lead", "conversion", "revenue"],
    "compliance": ["compliance", "regulation", "audit", "gdpr", "sox", "policy", "risk", "control"],
    "operational": ["operation", "process", "workflow", "sla", "incident", "ticket", "support"],
    "public": [],
}

SYSTEM_PROMPT = """You are a secure enterprise AI assistant. You answer questions using ONLY the provided context chunks.

Rules you must follow:
1. Ground every claim in the provided context — never hallucinate facts.
2. If the context doesn't contain enough information, say so explicitly.
3. Cite sources inline using [Source: <source_name>, Page/Row: <ref>] format.
4. Never reveal information from sources the user is not authorized to access.
5. Provide a confidence level (High / Medium / Low) at the end of each answer.
6. If the query asks for something outside your context, say "Insufficient data in authorized sources."

Format your response as:
ANSWER: <your grounded answer with inline citations>
SOURCES USED: <comma-separated list of source names>
CONFIDENCE: <High | Medium | Low>
REASONING: <brief note on how you derived the answer>
"""

USER_PROMPT = """User role: {role}
User question: {query}

Relevant context from authorized data sources:
{context}

Answer the question using only the context above."""


def route_query(query: str, allowed_sources: list[str]) -> list[str]:
    """
    Simple keyword-based routing to prioritise relevant data silos.
    Falls back to all allowed sources if no strong signal.
    """
    query_lower = query.lower()
    scores: dict[str, int] = {}
    for source in allowed_sources:
        keywords = SOURCE_ROUTING_HINTS.get(source, [])
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[source] = score

    if scores:
        # Return sources sorted by relevance, but always include all allowed
        prioritised = sorted(scores, key=lambda s: scores[s], reverse=True)
        ordered = prioritised + [s for s in allowed_sources if s not in prioritised]
        return ordered
    return allowed_sources


def format_context(docs: list[Document], scores: list[float]) -> str:
    """Format retrieved chunks into a clean context string with metadata."""
    if not docs:
        return "No relevant context found in authorized sources."

    parts = []
    for i, (doc, score) in enumerate(zip(docs, scores), 1):
        meta = doc.metadata
        source_name = meta.get("source_name", "Unknown")
        source_type = meta.get("source_type", "unknown")
        ref = meta.get("ref", f"chunk-{i}")
        relevance_pct = round(score * 100, 1)

        parts.append(
            f"[Chunk {i}] Source: {source_name} ({source_type}) | Ref: {ref} | Relevance: {relevance_pct}%\n"
            f"{doc.page_content.strip()}"
        )
    return "\n\n---\n\n".join(parts)


def parse_llm_response(raw: str) -> dict:
    """Extract structured fields from LLM response."""
    result = {
        "answer": raw,
        "sources_used": [],
        "confidence": "Low",
        "reasoning": "",
    }
    lines = raw.strip().split("\n")
    buffer = {}
    current_key = None

    for line in lines:
        if line.startswith("ANSWER:"):
            current_key = "answer"
            buffer[current_key] = line[len("ANSWER:"):].strip()
        elif line.startswith("SOURCES USED:"):
            current_key = "sources_used"
            raw_sources = line[len("SOURCES USED:"):].strip()
            buffer[current_key] = [s.strip() for s in raw_sources.split(",") if s.strip()]
        elif line.startswith("CONFIDENCE:"):
            current_key = "confidence"
            buffer[current_key] = line[len("CONFIDENCE:"):].strip()
        elif line.startswith("REASONING:"):
            current_key = "reasoning"
            buffer[current_key] = line[len("REASONING:"):].strip()
        elif current_key and line.strip():
            if isinstance(buffer.get(current_key), str):
                buffer[current_key] += " " + line.strip()

    result.update(buffer)
    return result


def maybe_query_postgres(query: str, user: UserContext) -> Optional[dict]:
    """
    For analytical/numeric queries, run a text-to-SQL pass against Postgres
    and add the result as live context. Returns dict with sql + rows, or None.
    """
    structured_sources = {"finance_reports", "hr_records", "sales_data"}
    if not (set(user.allowed_sources) & structured_sources):
        return None

    # Cheap signal: does the query feel analytical?
    analytical_kw = ["how many", "count", "sum", "total", "average", "list all",
                     "top ", "highest", "lowest", "compare", "between"]
    if not any(kw in query.lower() for kw in analytical_kw):
        return None

    try:
        from app.core.postgres_source import get_schema_summary, run_sql
        schema = get_schema_summary()
        if not schema.strip():
            return None

        llm = ChatOpenAI(model=LLM_MODEL, temperature=0, max_tokens=300)
        sql_prompt = (
            "You are a SQL generator. Given the PostgreSQL schema below, write ONE read-only "
            "SELECT query that answers the user's question. Return ONLY the SQL, no explanation, "
            "no markdown fences. Use LIMIT 50.\n\n"
            f"SCHEMA:\n{schema}\n\n"
            f"USER QUESTION: {query}\n\nSQL:"
        )
        sql_resp = llm.invoke(sql_prompt).content.strip()
        # Strip code fences if present
        sql_resp = sql_resp.replace("```sql", "").replace("```", "").strip()

        rows = run_sql(sql_resp, max_rows=50)
        return {"sql": sql_resp, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"sql": None, "rows": [], "error": str(e)}


def run_rag_query(query: str, user: UserContext, k: int = 5) -> dict:
    routed_sources = route_query(query, user.allowed_sources)

    retrieve_fn = rbac_retriever(user.role, k=k)
    docs, scores = retrieve_fn(query)

    context_str = format_context(docs, scores)

    pg_result = maybe_query_postgres(query, user)
    if pg_result and pg_result.get("rows"):
        pg_block = (
            f"\n\n---\n\n[Live SQL Query Result from PostgreSQL]\n"
            f"SQL: {pg_result['sql']}\n"
            f"Rows returned: {pg_result['row_count']}\n"
            f"Data: {json.dumps(pg_result['rows'], default=str, indent=2)}"
        )
        context_str = context_str + pg_block

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1, max_tokens=1500)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm
    response = chain.invoke({
        "role": user.role.value,
        "query": query,
        "context": context_str,
    })

    raw_text = response.content
    parsed = parse_llm_response(raw_text)

    retrieved_chunks = [
        {
            "source_name": doc.metadata.get("source_name", "unknown"),
            "source_type": doc.metadata.get("source_type", "unknown"),
            "ref": doc.metadata.get("ref", ""),
            "relevance_score": round(score, 4),
            "snippet": doc.page_content[:200] + ("..." if len(doc.page_content) > 200 else ""),
        }
        for doc, score in zip(docs, scores)
    ]

    return {
        "query": query,
        "user": user.username,
        "role": user.role.value,
        "answer": parsed["answer"],
        "sources_used": parsed["sources_used"],
        "confidence": parsed["confidence"],
        "reasoning": parsed["reasoning"],
        "retrieved_chunks": retrieved_chunks,
        "routed_sources": routed_sources,
        "total_chunks_retrieved": len(docs),
        "postgres_query": pg_result if pg_result else None,
    }
