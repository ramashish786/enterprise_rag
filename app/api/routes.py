# app/api/routes.py
# FastAPI endpoint definitions

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import secrets

from app.core.rbac import authenticate_user, UserContext, USERS, ROLE_PERMISSIONS, DataSource
from app.core.rag_pipeline import run_rag_query
from app.core.ingestion import ingest_file
from app.core.vectorstore import collection_stats

router = APIRouter()
security = HTTPBasic()


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> UserContext:
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


class QueryRequest(BaseModel):
    query: str
    k: Optional[int] = 5


class QueryResponse(BaseModel):
    query: str
    user: str
    role: str
    answer: str
    sources_used: list[str]
    confidence: str
    reasoning: str
    retrieved_chunks: list[dict]
    routed_sources: list[str]
    total_chunks_retrieved: int


@router.get("/health")
def health():
    return {"status": "ok", "service": "Enterprise RAG Intelligence System"}


@router.get("/me")
def whoami(user: UserContext = Depends(get_current_user)):
    """Return current user identity and permissions."""
    return {
        "username": user.username,
        "name": user.name,
        "role": user.role.value,
        "allowed_sources": user.allowed_sources,
    }


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, user: UserContext = Depends(get_current_user)):
    """Run a RAG query against the user's authorized data sources."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    k = max(1, min(request.k or 5, 20))  # clamp between 1-20
    result = run_rag_query(request.query, user, k=k)
    return result


@router.post("/ingest")
def ingest(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    user: UserContext = Depends(get_current_user),
):
    """Upload and index a document. Admin only."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can ingest documents")

    valid_types = [ds.value for ds in DataSource]
    if source_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type. Must be one of: {valid_types}",
        )

    file_bytes = file.file.read()
    try:
        result = ingest_file(file_bytes, file.filename, source_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return result


@router.get("/stats")
def stats(user: UserContext = Depends(get_current_user)):
    """Collection statistics. Admins see all; others see their allowed sources."""
    base = collection_stats()
    if user.role.value == "admin":
        return {**base, "all_sources": [ds.value for ds in DataSource]}
    return {**base, "your_allowed_sources": user.allowed_sources}


@router.get("/sources")
def list_sources():
    """Public endpoint: list all available data source types."""
    return {"sources": [ds.value for ds in DataSource]}


@router.get("/postgres/tables")
def postgres_tables(user: UserContext = Depends(get_current_user)):
    """List available tables in the connected Postgres instance."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    try:
        from app.core.postgres_source import list_tables, get_schema_summary
        return {"tables": list_tables(), "schema": get_schema_summary()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Postgres unavailable: {e}")


class PgIngestRequest(BaseModel):
    table_name: str
    source_type: str
    limit: Optional[int] = 1000


@router.post("/postgres/ingest")
def postgres_ingest(req: PgIngestRequest, user: UserContext = Depends(get_current_user)):
    """Index a Postgres table into the vector store."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can ingest")
    valid = [ds.value for ds in DataSource]
    if req.source_type not in valid:
        raise HTTPException(status_code=400, detail=f"source_type must be one of {valid}")
    try:
        from app.core.postgres_source import ingest_table
        return ingest_table(req.table_name, req.source_type, req.limit or 1000)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
def list_roles(user: UserContext = Depends(get_current_user)):
    """Admin-only: show all roles and their permissions."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return {
        role: sources
        for role, sources in ROLE_PERMISSIONS.items()
    }
