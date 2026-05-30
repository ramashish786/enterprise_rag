# Enterprise RAG Intelligence System

A production-grade, secure **Retrieval-Augmented Generation (RAG)** pipeline built with FastAPI, LangChain, ChromaDB, PostgreSQL, and **OpenAI GPT-4o**. Enforces strict role-based access control (RBAC) across heterogeneous enterprise data sources: PDFs, CSVs, JSON, text documents, and a live SQL database.

---

## Architecture

```
┌──────────────┐    Basic Auth     ┌──────────────────────┐
│  Browser UI  │ ─────────────────►│  FastAPI Backend     │
└──────────────┘                   └──────────┬───────────┘
                                              │
                       ┌──────────────────────▼──────────────────────┐
                       │              RBAC Enforcement               │
                       │  role → allowed data sources (3-layer guard)│
                       └──────────────────────┬──────────────────────┘
                                              │
                       ┌──────────────────────▼──────────────────────┐
                       │              RAG Pipeline                   │
                       │  1. Query routing                           │
                       │  2. Semantic retrieval (ChromaDB)           │
                       │  3. Live SQL augmentation (Postgres) ◄──┐   │
                       │  4. Context assembly with citations     │   │
                       │  5. LLM generation (OpenAI GPT-4o)      │   │
                       └─────────┬────────────────────────┬──────┴───┘
                                 │                        │
                  ┌──────────────▼─────────┐   ┌──────────▼───────────┐
                  │   ChromaDB (vectors)   │   │  PostgreSQL (live)   │
                  │  PDFs/CSV/JSON/TXT     │   │  employees,          │
                  │  + indexed PG rows     │   │  sales_deals,        │
                  │                        │   │  finance_quarterly   │
                  └────────────────────────┘   └──────────────────────┘
```

## Data Sources (All Requirement Types Covered)

| Type | Files / Tables | Mapped Source |
|------|----------------|---------------|
| **PDF** | `annual_report_2023.pdf` | finance_reports |
| **CSV** | `department_budgets_q1_2024.csv`, `sales_pipeline_q1_2024.csv`, `user_role_mappings.csv` | finance / sales / public |
| **JSON logs** | `audit_trail.json`, `employee_records.json` | compliance / hr |
| **Text** | financial report, HR policy, platform docs, legal MSA, compliance policy | various |
| **Access policies** | `access_policies.json` | compliance |
| **PostgreSQL tables** | `employees`, `sales_deals`, `finance_quarterly` | hr / sales / finance |

## Project Structure

```
enterprise_rag/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── app/
│   ├── main.py                  ← FastAPI entry + static frontend
│   ├── api/routes.py            ← /query, /ingest, /me, /postgres/*
│   └── core/
│       ├── rbac.py              ← Roles + permissions + auth
│       ├── vectorstore.py       ← ChromaDB + RBAC-filtered retriever
│       ├── ingestion.py         ← PDF / CSV / JSON / TXT loaders
│       ├── postgres_source.py   ← Postgres schema, ingest, text-to-SQL
│       └── rag_pipeline.py      ← Routing → retrieval → generation
├── data/synthetic/generate_data.py
├── frontend/index.html          ← Single-page web UI
├── scripts/ingest_all.py        ← Generate + index all data
└── tests/test_rag_system.py
```

---

## Quick Start (Docker — recommended)

### 1. Get an OpenAI API key
Get a key from https://platform.openai.com/api-keys.

### 2. Create `.env` file
```bash
cp .env.example .env
```
Edit `.env` and set:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini
```

> `gpt-4o-mini` is fast and cheap. For higher quality use `gpt-4o`.

### 3. Build and run
```bash
docker-compose up --build
```

This starts **two containers**:
- `rag-postgres` — PostgreSQL 16 with seeded enterprise tables
- `enterprise-rag` — FastAPI app + ChromaDB + frontend

On first start (~60 sec):
1. Postgres initialises the database
2. App generates 12 synthetic data files
3. Indexes everything into ChromaDB
4. Loads Postgres tables and seeds rows
5. Starts the API server

### 4. Open the app
- **Web UI:** http://localhost:8000
- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/api/v1/health

### 5. Sign in
Use any demo user from the sidebar (click to auto-fill):

| Username | Password | Role | Can access |
|----------|----------|------|-----------|
| frank | frank123 | admin | **all data** |
| alice | alice123 | finance | finance, compliance, operational |
| bob | bob123 | hr | hr, compliance |
| carol | carol123 | engineering | engineering, operational |
| dave | dave123 | legal | legal, compliance, hr |
| eve | eve123 | sales | sales, operational |
| guest | guest123 | viewer | public only |

---

## How the LLM Uses Each Data Source

### A. Vectorised documents (ChromaDB)
PDF / CSV / JSON / TXT files get chunked, embedded with sentence-transformers (`all-MiniLM-L6-v2`), and indexed with `source_type` metadata. On query:
1. RBAC filter restricts ChromaDB search to user's allowed sources
2. Top-k chunks retrieved by semantic similarity
3. Sent to LLM as context with citations

### B. PostgreSQL (two paths)
**Path 1 — Indexed rows.** On startup, every row from `employees`, `sales_deals`, `finance_quarterly` is serialised as a Document and indexed alongside the files. So PostgreSQL data appears in semantic search results too.

**Path 2 — Live text-to-SQL.** For analytical queries ("how many", "total", "top", "compare"), the pipeline:
1. Pulls live schema from Postgres
2. Asks GPT-4o-mini to write a SELECT query
3. Validates it's read-only, executes (capped at 50 rows)
4. Injects the SQL result into the LLM context as a `[Live SQL Query Result]` block

The final LLM prompt contains **both** retrieved chunks AND live SQL results, so answers can combine narrative context (from PDFs/policies) with fresh structured data (from Postgres).

---

## Try It Out

### Example queries by role

**As Alice (finance):**
```
"What was the Q1 2024 revenue and which department exceeded budget?"
```
→ Returns finance report excerpts + budget CSV rows.

**As Eve (sales) — triggers live SQL:**
```
"How many deals are in the pipeline and what is the total ACV?"
```
→ GPT generates `SELECT COUNT(*), SUM(acv_usd) FROM sales_deals`, executes it, includes results in answer with confidence score.

**As Bob (HR) — RBAC denial demo:**
```
"What was the Q1 revenue?"
```
→ Returns "Insufficient data in authorized sources" — finance_reports filtered out at retrieval time.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/health` | None | Health check |
| GET | `/api/v1/me` | Basic | Current user identity & permissions |
| POST | `/api/v1/query` | Basic | Main RAG endpoint |
| POST | `/api/v1/ingest` | Admin | Upload & index a file |
| GET | `/api/v1/stats` | Basic | Collection stats |
| GET | `/api/v1/sources` | None | List data source types |
| GET | `/api/v1/roles` | Admin | All role → permission mappings |
| GET | `/api/v1/postgres/tables` | Admin | List Postgres tables + schema |
| POST | `/api/v1/postgres/ingest` | Admin | Index a Postgres table |

### Example curl
```bash
# Identity check
curl -u alice:alice123 http://localhost:8000/api/v1/me

# Query (live SQL kicks in for analytical questions)
curl -u eve:eve123 \
  -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total pipeline value of open deals?"}'
```

---

## Response Format

```json
{
  "query": "What is total pipeline value?",
  "user": "eve",
  "role": "sales",
  "answer": "Total open pipeline value is $1.9M [Source: sales_deals]...",
  "sources_used": ["sales_deals", "sales_pipeline_q1_2024"],
  "confidence": "High",
  "reasoning": "Aggregated from live SQL query and CSV data.",
  "retrieved_chunks": [
    {
      "source_name": "postgres.sales_deals",
      "source_type": "sales_data",
      "ref": "row-3",
      "relevance_score": 0.91,
      "snippet": "deal_id: DL-006 | account: MegaCorp | acv_usd: 1200000..."
    }
  ],
  "routed_sources": ["sales_data", "operational", "public"],
  "total_chunks_retrieved": 5,
  "postgres_query": {
    "sql": "SELECT SUM(acv_usd) FROM sales_deals WHERE stage != 'Closed Won'",
    "rows": [{"sum": 1900000}],
    "row_count": 1
  }
}
```

---

## Run Without Docker (Local Python)

```bash
# 1. Postgres (or use a local instance — adjust POSTGRES_URL in .env)
docker run -d --name pg -p 5432:5432 \
  -e POSTGRES_USER=rag -e POSTGRES_PASSWORD=rag -e POSTGRES_DB=enterprise \
  postgres:16-alpine

# 2. Python environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
echo "POSTGRES_URL=postgresql+psycopg2://rag:rag@localhost:5432/enterprise" >> .env
# Edit OPENAI_API_KEY in .env

# 4. Generate data & index
python scripts/ingest_all.py

# 5. Start server
uvicorn app.main:app --reload --port 8000
```

---

## Run Tests

```bash
pytest tests/test_rag_system.py -v
```

Covers: authentication, RBAC enforcement across roles, cross-role denial, multi-format ingestion, query routing, response parsing, security regression tests.

---

## RBAC — How It Works

**3 layers of enforcement:**

1. **Endpoint guard.** Every protected route requires `get_current_user`. Admin-only routes check `user.role == admin`.
2. **ChromaDB filter.** Retrieval passes `{"source_type": {"$in": allowed}}` so the DB never returns unauthorized chunks.
3. **Python double-check.** After retrieval, every chunk's metadata is re-verified against `allowed_sources`. Belt-and-suspenders against filter bypass bugs.
4. **Postgres text-to-SQL gate.** SQL generation only runs if the user has access to a structured source (`finance_reports`, `hr_records`, `sales_data`).

A user can never see data they're not authorized for — the LLM literally doesn't receive it.

---

## Stopping & Cleaning Up

```bash
docker-compose down            # stop containers, keep data
docker-compose down -v         # stop + wipe Postgres & ChromaDB volumes
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `OPENAI_API_KEY` not set | Edit `.env`, restart with `docker-compose up` |
| Postgres connection refused | Wait 30s — health check gates the app on Postgres readiness |
| Embedding model download slow on first build | Normal — `all-MiniLM-L6-v2` (~90MB) cached after first build |
| Frontend shows offline (red dot) | Backend still starting; refresh after ~60s |
| Empty answers | Run `docker-compose exec rag python scripts/ingest_all.py` |
| Rebuild from scratch | `docker-compose down -v && docker-compose up --build` |
