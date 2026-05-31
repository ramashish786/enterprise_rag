# Enterprise RAG Intelligence System — Architecture & Component Reference

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Directory Structure](#2-directory-structure)
3. [Entry Point — app/main.py](#3-entry-point--appmainpy)
4. [API Layer — app/api/routes.py](#4-api-layer--appapiroutespy)
5. [RBAC — app/core/rbac.py](#5-rbac--appcorerbacpy)
6. [Document Ingestion — app/core/ingestion.py](#6-document-ingestion--appcoreingestionpy)
7. [Vector Store — app/core/vectorstore.py](#7-vector-store--appcorevectorstorey)
8. [RAG Pipeline — app/core/rag_pipeline.py](#8-rag-pipeline--appcorerag_pipelinepy)
9. [PostgreSQL Source — app/core/postgres_source.py](#9-postgresql-source--appCorepostgres_sourcepy)
10. [Frontend — frontend/index.html](#10-frontend--frontendindexhtml)
11. [Infrastructure — docker-compose.yml & Dockerfile](#11-infrastructure--docker-composeyml--dockerfile)
12. [Synthetic Data — data/synthetic/](#12-synthetic-data--datasynthetic)
13. [Dependencies — requirements.txt](#13-dependencies--requirementstxt)
14. [Data & Request Flow (End-to-End)](#14-data--request-flow-end-to-end)
15. [Security Model](#15-security-model)
16. [User Guide](#16-user-guide)

---

## 1. System Overview

The Enterprise RAG Intelligence System is a Retrieval-Augmented Generation (RAG) application that lets employees query a company knowledge base using natural language. Every response is grounded in real documents and every document retrieval is gated by the user's role — no user can read data outside their department's authorisation.

The system has three cooperating layers:

```
User (browser)
      │  HTTP / Basic Auth
      ▼
FastAPI backend  ──────────────►  ChromaDB (vector search)
      │                                │ semantic chunks
      │  SQL when analytical           │
      ▼                                │
PostgreSQL (structured tables) ◄───────┘ (also indexed as chunks)
      │
      ▼
OpenAI LLM  (gpt-4o-mini / gpt-4o)
```

---

## 2. Directory Structure

```
enterprise_rag/
├── app/
│   ├── main.py                  # FastAPI app factory + server startup
│   ├── api/
│   │   └── routes.py            # All HTTP endpoints
│   └── core/
│       ├── rbac.py              # Roles, permissions, authentication
│       ├── ingestion.py         # File parsing and chunking
│       ├── vectorstore.py       # ChromaDB read/write + RBAC-filtered retrieval
│       ├── rag_pipeline.py      # Query routing, LLM prompting, response parsing
│       └── postgres_source.py   # PostgreSQL schema, seeding, text-to-SQL
├── frontend/
│   └── index.html               # Single-page web UI
├── data/
│   └── synthetic/               # Pre-generated sample documents
├── scripts/
│   └── ingest_all.py            # One-shot data generation + indexing
├── tests/
│   └── test_rag_system.py       # Unit and integration tests
├── docker-compose.yml           # Postgres + FastAPI service definitions
├── Dockerfile                   # Container image build
├── requirements.txt             # Python dependencies
└── .env                         # API keys and environment config
```

---

## 3. Entry Point — `app/main.py`

### What it does

Creates and configures the FastAPI application, registers middleware, mounts the frontend, and wires together all the API routes.

### Key responsibilities

| Responsibility | Detail |
|---|---|
| App factory | Creates the `FastAPI` instance with title, description, version |
| Lifespan hook | On startup, pre-loads the `all-MiniLM-L6-v2` embedding model so the first query isn't slow |
| CORS middleware | Allows any origin (`*`) — acceptable for an internal demo; restrict in production |
| Router mounting | Registers all endpoints from `routes.py` under the `/api/v1` prefix |
| Static files | Mounts the `frontend/` directory at `/static` and serves `index.html` at `/` |

### Why it exists

FastAPI applications need a single top-level `app` object that Uvicorn runs. Keeping this file thin — only wiring things together — keeps concerns separated from the actual business logic.

### Used by

- Uvicorn (the ASGI server) runs this file directly: `uvicorn app.main:app`
- The `Dockerfile` starts the server via this entry point

---

## 4. API Layer — `app/api/routes.py`

### What it does

Defines every HTTP endpoint the application exposes. It is the boundary between the outside world and the internal business logic.

### Endpoints

| Method | Path | Auth | Admin only | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/health` | None | No | Liveness check (used by Docker healthcheck) |
| GET | `/api/v1/me` | Basic | No | Returns the current user's name, role, allowed sources |
| POST | `/api/v1/query` | Basic | No | Main RAG query — returns grounded answer + citations |
| POST | `/api/v1/ingest` | Basic | Yes | Upload a file and index it into ChromaDB |
| GET | `/api/v1/stats` | Basic | No | Chunk count and authorised sources for the current user |
| GET | `/api/v1/sources` | None | No | Lists all 8 data source types |
| GET | `/api/v1/documents` | Basic | Yes | Lists all indexed documents with chunk counts |
| DELETE | `/api/v1/documents/{source_name}` | Basic | Yes | Deletes all chunks for a named document |
| GET | `/api/v1/postgres/tables` | Basic | Yes | Lists Postgres tables and schema |
| POST | `/api/v1/postgres/ingest` | Basic | Yes | Indexes a Postgres table into ChromaDB |
| GET | `/api/v1/roles` | Basic | Yes | Shows all roles and their permission sets |

### Authentication guard — `get_current_user`

Every protected endpoint calls `get_current_user()`, which is a FastAPI dependency. It:

1. Reads the `Authorization: Basic <base64>` header via FastAPI's built-in `HTTPBasic` security scheme
2. Calls `authenticate_user()` from `rbac.py`
3. Returns a `UserContext` (name, role, allowed sources) or raises HTTP 401

This means authentication is checked **before** any endpoint logic runs.

### Why it exists

Separating endpoints into their own module (`routes.py`) keeps `main.py` clean and makes it easy to add new endpoints, versioning, or split into multiple routers without touching the app factory.

### Used by

- `main.py` registers this router: `app.include_router(router, prefix="/api/v1")`
- The frontend calls every endpoint listed above via `fetch`

---

## 5. RBAC — `app/core/rbac.py`

### What it does

Defines who the users are, what roles exist, which data sources each role can see, and provides the functions to authenticate a user and look up their permissions.

### Core components

**`Role` (Enum)**

Seven roles: `admin`, `finance`, `hr`, `engineering`, `legal`, `sales`, `viewer`. Using an Enum rather than plain strings prevents typos from silently creating a broken permission.

**`DataSource` (Enum)**

Eight source tags: `finance_reports`, `hr_records`, `engineering_docs`, `legal_contracts`, `sales_data`, `compliance`, `operational`, `public`. Every document stored in ChromaDB is tagged with one of these values so that retrieval can be filtered by it.

**`ROLE_PERMISSIONS` (dict)**

The central access-control table. Maps each role to the list of `DataSource` values it may read:

```
admin        →  all 8 sources
finance      →  finance_reports, compliance, operational, public
hr           →  hr_records, compliance, public
engineering  →  engineering_docs, operational, public
legal        →  legal_contracts, compliance, hr_records, public
sales        →  sales_data, operational, public
viewer       →  public only
```

**`USERS` (dict)**

A hardcoded registry of 7 demo users (username → password, role, display name). In a production system this would be replaced by a real identity provider (LDAP, OAuth, etc.).

**`UserContext` (Pydantic model)**

A typed object carrying `username`, `name`, `role`, and `allowed_sources` for the duration of a request. Passed through the entire call stack so every layer knows exactly what the caller is allowed to see.

**`authenticate_user()`**

Looks up the username in `USERS`, checks the password, and returns a fully populated `UserContext`. Returns `None` on failure (the API layer converts that to HTTP 401).

**`get_allowed_sources()` / `can_access_source()`**

Utility helpers used by `vectorstore.py` and `rag_pipeline.py` to check permissions without touching `ROLE_PERMISSIONS` directly.

### Why it exists

All access-control logic is centralised here so that changing a permission (e.g. giving the `legal` role access to `finance_reports`) requires editing exactly one dict in one file, with no risk of missing a scattered check elsewhere.

### Used by

- `routes.py` — `authenticate_user()` inside `get_current_user()`
- `vectorstore.py` — `get_allowed_sources()` to build the ChromaDB `where` filter
- `rag_pipeline.py` — `UserContext` flows through the entire query execution
- `frontend/index.html` — role value determines which nav items and panels are shown

---

## 6. Document Ingestion — `app/core/ingestion.py`

### What it does

Reads raw file bytes in any supported format, extracts text, splits it into chunks, attaches metadata, and adds those chunks to ChromaDB.

### File format support

| Extension | Parser | How text is extracted |
|---|---|---|
| `.pdf` | `pypdf.PdfReader` | Page-by-page text extraction; empty pages skipped |
| `.csv` | `csv.DictReader` | Each row becomes one document: `"col: val \| col: val"` |
| `.json` / `.jsonl` | `json.loads` / NDJSON fallback | Arrays of objects; each item is pretty-printed JSON then chunked |
| `.txt` / `.md` | Plain decode | Entire file chunked as text |

### Text splitter

`RecursiveCharacterTextSplitter` from LangChain with:

- **Chunk size:** 600 characters
- **Overlap:** 80 characters
- **Separators:** `["\n\n", "\n", ". ", " ", ""]`

The overlap ensures that a sentence split across two chunk boundaries is still retrievable by either half. The separator cascade tries to split on paragraph breaks first, then line breaks, then sentences, then words — preserving as much semantic coherence as possible.

### Metadata attached to every chunk

```python
{
    "source_name":  "q1_2024_finance_report",   # filename stem (or "postgres.employees")
    "source_type":  "finance_reports",           # DataSource enum value
    "ref":          "page-2-chunk-3",            # location within the source
    "file_type":    "pdf",                       # original format
}
```

This metadata is how RBAC filtering works at retrieval time: ChromaDB is told `WHERE source_type IN [allowed list]`.

### `ingest_file()` — main entry point

1. Detects file extension and selects the appropriate parser from `INGESTOR_MAP`
2. Calls the parser to produce a list of `Document` objects
3. Calls `add_documents()` in `vectorstore.py` to write them to ChromaDB
4. Returns a summary dict `{ status, file, source_type, chunks_indexed, file_type }`

### `ingest_directory()` — batch helper

Walks a directory recursively and calls `ingest_file()` for every supported file. Used by `scripts/ingest_all.py` at Docker startup.

### Why it exists

Different file formats need different parsing strategies, but the rest of the system only needs to work with a flat list of `Document` objects. Isolating format handling here means adding a new format (e.g. DOCX) requires only adding one function and one entry in `INGESTOR_MAP`.

### Used by

- `routes.py` → `POST /ingest` endpoint calls `ingest_file()`
- `scripts/ingest_all.py` calls `ingest_directory()` on startup

---

## 7. Vector Store — `app/core/vectorstore.py`

### What it does

All reads and writes to ChromaDB go through this module. It owns the collection configuration, the embedding model, and the RBAC-filtered retrieval logic.

### Key functions

**`get_chroma_client()`**

Creates a `chromadb.PersistentClient` pointing at `./chroma_db` (or `CHROMA_PERSIST_DIR` env var). Persistence means data survives server restarts.

**`get_vectorstore()`**

Returns a LangChain `Chroma` wrapper around the raw ChromaDB client. The LangChain wrapper handles generating embeddings automatically when documents are added or queries are run.

**`get_embedding_function()`**

Returns a `SentenceTransformerEmbeddings` instance using `all-MiniLM-L6-v2`, a 384-dimension model that runs locally (no API calls, no cost, low latency). This same model is used for both indexing and querying — consistency is mandatory for meaningful similarity scores.

**`add_documents(docs)`**

Calls `vectorstore.add_documents()` which embeds each chunk and stores the vector alongside its text and metadata in ChromaDB. Returns the count of documents added.

**`rbac_retriever(role, k)`**

Returns a closure (a function) that, when called with a query string:

1. Looks up the role's `allowed_sources` via `rbac.get_allowed_sources()`
2. Passes `{ "source_type": { "$in": allowed_sources } }` as a `where` filter to ChromaDB — this is enforced at the database level
3. Over-fetches `k*2` results to account for the filter reducing the result set
4. Re-checks every returned chunk's `source_type` against the allowed list in Python (double-guard — ChromaDB filters are best-effort, not guaranteed)
5. Sorts by relevance score and returns the top `k`

**`collection_stats()`**

Returns the total chunk count and collection name. Used by the `/stats` endpoint and displayed on the System Stats panel.

**`list_documents()`**

Fetches all metadata from ChromaDB, groups chunks by `source_name`, and returns a list of `{ source_name, source_type, chunk_count }` dicts. Used by the Manage Documents panel.

**`delete_document(source_name)`**

Queries ChromaDB for all chunk IDs where `source_name == <value>`, deletes them, and returns the count. Used by the admin delete endpoint.

### ChromaDB collection

- **Name:** `enterprise_rag`
- **Embedding model:** `all-MiniLM-L6-v2` (384 dimensions)
- **Storage path:** `./chroma_db` (Docker: `/app/chroma_db`, persisted as a volume)

### Why it exists

ChromaDB has its own Python client API and LangChain has its own wrapper. Putting all ChromaDB interaction behind a single module means the rest of the app never imports `chromadb` or deals with collection names, paths, or embedding model wiring. Swapping ChromaDB for another vector database (Pinecone, Weaviate, etc.) would require changes only here.

### Used by

- `ingestion.py` — calls `add_documents()`
- `rag_pipeline.py` — calls `rbac_retriever()`
- `postgres_source.py` — calls `add_documents()` when indexing a Postgres table
- `routes.py` — calls `collection_stats()`, `list_documents()`, `delete_document()`
- `main.py` — calls `get_embedding_function()` on startup to pre-warm the model

---

## 8. RAG Pipeline — `app/core/rag_pipeline.py`

### What it does

Orchestrates the full question-answering flow: from a raw user query to a structured, cited, confidence-rated answer. This is the core intelligence of the system.

### Pipeline stages

```
run_rag_query(query, user, k)
    │
    ├── 1. route_query()          keyword match → ordered source list
    │
    ├── 2. rbac_retriever()       vector search → top-k chunks (RBAC-filtered)
    │
    ├── 3. format_context()       chunk list → readable context string
    │
    ├── 4. maybe_query_postgres() (optional) analytical query → live SQL result
    │
    ├── 5. ChatOpenAI.invoke()    system prompt + context + question → raw LLM text
    │
    └── 6. parse_llm_response()   raw text → { answer, sources, confidence, reasoning }
```

### `route_query(query, allowed_sources)`

A lightweight keyword-scoring function. For each allowed source, it counts how many of that source's hint-keywords appear in the query. Sources with more keyword matches are placed first in the ordered list returned.

This does **not** restrict retrieval — ChromaDB always searches all allowed sources. The ordering is a hint to the user about which silos were most relevant, shown in the frontend as "routed sources".

Example: if the query is "What was Q1 revenue?", `finance_reports` scores high on "revenue" and "quarter", so it appears first in the routing list.

### `format_context(docs, scores)`

Converts a list of `Document` objects and their similarity scores into a structured text block. Each chunk is formatted as:

```
[Chunk 1] Source: q1_2024_finance_report (finance_reports) | Ref: page-2-chunk-3 | Relevance: 87.4%
<chunk text here>

---

[Chunk 2] ...
```

This format is passed directly into the LLM prompt. The explicit metadata (source name, ref, relevance) lets the LLM produce accurate inline citations like `[Source: q1_2024_finance_report, Page/Row: page-2-chunk-3]`.

### `maybe_query_postgres(query, user)`

An optional augmentation step that runs **only** when:

1. The user has access to at least one structured source (`finance_reports`, `hr_records`, or `sales_data`)
2. The query contains analytical keywords like "how many", "total", "sum", "compare", etc.

When both conditions are met, it:

1. Asks the LLM to generate a `SELECT` SQL query given the Postgres schema
2. Validates that the generated SQL starts with `SELECT` (blocks `DELETE`, `UPDATE`, etc.)
3. Executes it via `postgres_source.run_sql()` (capped at 50 rows)
4. Appends the live tabular result to the context string before calling the main LLM

This means analytical questions (e.g. "What is the total ACV of deals in Negotiation?") can return precise, real-time numbers rather than relying on potentially stale text chunks.

### System prompt (SYSTEM_PROMPT)

The LLM is instructed to:

- Answer using **only** the provided context (no hallucination)
- Say "Insufficient data in authorized sources" if context is lacking
- Cite sources inline using the `[Source: ..., Page/Row: ...]` format
- Output in a structured format: `ANSWER:`, `SOURCES USED:`, `CONFIDENCE:`, `REASONING:`
- Never reveal unauthorised information (defence-in-depth on top of RBAC filtering)

### `parse_llm_response(raw)`

Parses the structured LLM output into a Python dict. It reads the response line-by-line, detects the labelled sections (`ANSWER:`, `SOURCES USED:`, etc.), and handles multi-line answers by appending continuation lines to the current section.

### LLM configuration

- **Model:** `gpt-4o-mini` by default (configurable via `LLM_MODEL` env var)
- **Temperature:** `0.1` (near-deterministic — reduces hallucination in factual Q&A)
- **Max tokens:** `1500` (enough for a detailed answer with citations)

### Why it exists

RAG is not just "retrieve chunks + call LLM". It requires routing, RBAC filtering, context formatting, optional structured data augmentation, prompt engineering, and response parsing. Putting all this in one file makes the full query lifecycle easy to trace, test, and modify.

### Used by

- `routes.py` → `POST /query` endpoint calls `run_rag_query()`

---

## 9. PostgreSQL Source — `app/core/postgres_source.py`

### What it does

Manages everything to do with the relational database: schema definition, demo data seeding, table-to-document indexing, and live SQL execution.

### Key functions

**`get_engine()`**

Creates a SQLAlchemy engine connected to the Postgres instance using the `POSTGRES_URL` environment variable. `pool_pre_ping=True` drops stale connections automatically.

**`init_demo_schema()`**

Creates three tables if they don't exist and seeds them with demo rows using `ON CONFLICT DO NOTHING` — safe to run multiple times on startup.

Tables:
- `employees` — 7 columns: employee_id, name, department, level, salary, start_date, status
- `sales_deals` — 7 columns: deal_id, account, ACV, stage, close_date, owner, probability
- `finance_quarterly` — 5 columns: quarter, revenue, opex, EBITDA, net profit

**`ingest_table(table_name, source_type, limit)`**

Reads up to `limit` rows from a Postgres table and converts each row into a LangChain `Document`:

```
"employee_id: EMP1001 | name: James Li | department: Engineering | ..."
```

These documents are indexed into ChromaDB with `source_name = "postgres.employees"` so the same RBAC filtering that applies to files also applies to database rows.

**`run_sql(query, max_rows)`**

Executes a raw SQL string. It enforces read-only access by rejecting any query that doesn't start with `SELECT`. Returns rows as a list of dicts. Called by `maybe_query_postgres()` in the RAG pipeline.

**`get_schema_summary()`**

Introspects the live Postgres schema via SQLAlchemy and returns a human-readable string like:

```
Table employees(employee_id TEXT, name TEXT, department TEXT, ...)
Table sales_deals(deal_id TEXT, account TEXT, acv_usd INTEGER, ...)
```

This string is injected into the text-to-SQL prompt so the LLM knows what columns exist.

**`list_tables()` / `get_schema_summary()`**

Used by the `/postgres/tables` admin endpoint so an admin can see what structured data is available before deciding to index it.

### Why it exists

The system supports two types of data: unstructured documents (PDFs, CSVs, etc. in ChromaDB) and structured relational data (Postgres). Both are needed because semantic search is good for "what does the MSA say about liability?" but poor for "what is the exact total revenue across all Q1 deals?". PostgreSQL handles the latter with precision.

### Used by

- `scripts/ingest_all.py` — calls `init_demo_schema()` and `ingest_table()` on startup
- `rag_pipeline.py` — calls `get_schema_summary()` and `run_sql()` in the text-to-SQL path
- `routes.py` — `/postgres/tables` and `/postgres/ingest` endpoints

---

## 10. Frontend — `frontend/index.html`

### What it does

A self-contained single-page application delivered as one HTML file. It provides a chat interface, a document upload form, a system stats dashboard, and a document management panel — all in a dark-themed UI.

### Panels

**Query Assistant** (`panel-chat`)

The main interface. The user types a question, the frontend calls `POST /query`, and the response is rendered as a chat bubble with:
- The grounded answer
- Inline reasoning block
- Confidence badge (colour-coded: green = High, amber = Medium, red = Low)
- Source badges (one per cited document)
- Collapsible "retrieved chunks" section showing each chunk's source, relevance score (%), and snippet

**Ingest Document** (`panel-ingest`)

An admin-only form with a drag-and-drop file zone and a source type selector. Submits to `POST /ingest` via `FormData`. Displays success (chunk count) or error in a styled result block.

**Manage Documents** (`panel-docs`) — admin only

Shows a table of all indexed documents returned by `GET /documents`. Each row has the document name, source type, chunk count, and a Delete button. Clicking Delete triggers a `confirm()` dialog, then `DELETE /documents/{source_name}`, then refreshes the list.

**System Stats** (`panel-stats`)

Three stat cards (total chunks, user's role, collection name) plus a table of the current user's authorised sources with descriptions. Populated by `GET /stats`.

### Authentication

- Login form with username/password fields + quick-login demo user buttons
- On successful login, stores `{ username, password }` in `localStorage` so the session survives page refreshes
- On page load, reads `localStorage`, calls `GET /me` to validate, and restores the session silently
- On logout, clears `localStorage` and resets the UI
- All API calls include `Authorization: Basic <base64(user:pass)>` via the `authHeader()` helper

### Role-based UI visibility

- The **Manage Documents** nav item is shown only when `me.role === 'admin'`
- Other non-admin users never see or can navigate to the delete functionality — the server enforces this too, but the UI respects it as well

### Why it exists as one file

Keeping the entire frontend in a single HTML file makes deployment trivial — FastAPI serves it as a static file, no build step, no bundler, no Node.js needed. For a demo/enterprise-internal tool this is a pragmatic choice.

### Used by

- Served by FastAPI's static file middleware at `GET /`
- Communicates with all `/api/v1/*` endpoints

---

## 11. Infrastructure — `docker-compose.yml` & `Dockerfile`

### `docker-compose.yml`

Defines two services:

**`postgres`**

- Image: `postgres:16-alpine`
- Creates database `enterprise` with user/password `rag/rag`
- Persists data in the `pg_data` named volume
- Health-checked every 5 seconds via `pg_isready` — the `rag` service won't start until this passes

**`rag`**

- Builds the `Dockerfile` in the project root
- Depends on `postgres` being healthy before starting
- Mounts the `chroma_data` volume at `/app/chroma_db` so vector data persists across container restarts
- Mounts `./data/synthetic` so generated files are accessible inside the container
- Injects environment variables: `OPENAI_API_KEY`, `LLM_MODEL`, `CHROMA_PERSIST_DIR`, `POSTGRES_URL`
- Health-checked via `GET /api/v1/health` — allows 90 seconds startup time for data generation and indexing

### `Dockerfile`

1. Starts from `python:3.11-slim`
2. Installs all Python dependencies from `requirements.txt`
3. Pre-downloads the `all-MiniLM-L6-v2` embedding model into the image layer (so first-run is fast)
4. Copies all application code
5. On container start: runs `scripts/ingest_all.py` (generates synthetic data and indexes it), then starts the Uvicorn server

### Why Docker Compose

Running the two services together (Postgres + FastAPI) with a single `docker compose up` makes local setup a one-command operation. The health-check dependency chain ensures correct startup order.

---

## 12. Synthetic Data — `data/synthetic/`

### What it is

Twelve pre-generated files that populate the knowledge base on first startup:

| File | Source Type | Content |
|---|---|---|
| `q1_2024_finance_report.txt` | `finance_reports` | Q1 revenue, expenses, variance |
| `department_budgets_q1_2024.csv` | `finance_reports` | Budget vs actuals per department |
| `annual_report_2023.pdf` | `finance_reports` | Full-year 2023 financial summary |
| `employee_records.json` | `hr_records` | 15 employees with salaries and departments |
| `hr_policy_manual.txt` | `hr_records` | Leave, reviews, compensation bands |
| `platform_architecture.txt` | `engineering_docs` | System design, services, deployment |
| `audit_trail.json` | `compliance` | 50 timestamped compliance events |
| `msa_nexus_ventures_2024.txt` | `legal_contracts` | Service agreement with payment terms |
| `sales_pipeline_q1_2024.csv` | `sales_data` | 10 deals with stages and ACV |
| `compliance_policy.txt` | `compliance` | GDPR, SOX, data retention policy |
| `access_policies.json` | `compliance` | Data classification and role access rules |
| `user_role_mappings.csv` | `public` | 7 demo users with roles |

### `generate_data.py`

A script that generates all twelve files programmatically using Python's standard library and `reportlab` (for PDF generation). The data is realistic-looking but entirely fictional.

### `scripts/ingest_all.py`

Orchestrates the full setup:

1. Calls `generate_data.py` to create the files
2. Calls `ingestion.ingest_directory()` on each file with the correct source type tag
3. Calls `postgres_source.init_demo_schema()` to create and seed the database tables
4. Calls `postgres_source.ingest_table()` to also index the Postgres rows into ChromaDB

This runs once inside the Docker container before the API server starts.

---

## 13. Dependencies — `requirements.txt`

| Package | Version | Role |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework — routing, validation, dependency injection |
| `uvicorn[standard]` | 0.29.0 | ASGI server that runs the FastAPI app |
| `langchain` | 0.2.6 | Core LangChain primitives (`Document`, prompt templates, chains) |
| `langchain-core` | 0.2.10 | Base types used by LangChain integrations |
| `langchain-community` | 0.2.6 | ChromaDB vector store wrapper |
| `langchain-openai` | 0.1.14 | `ChatOpenAI` LLM integration |
| `langchain-text-splitters` | 0.2.2 | `RecursiveCharacterTextSplitter` for chunking |
| `sentence-transformers` | 3.0.1 | Local embedding model (`all-MiniLM-L6-v2`) |
| `chromadb` | 0.5.3 | Persistent vector database |
| `pydantic` | 2.7.4 | Data validation for API models and `UserContext` |
| `python-multipart` | 0.0.9 | Required by FastAPI to handle file upload form data |
| `pypdf` | 4.2.0 | PDF text extraction |
| `pandas` | 2.2.2 | Used in synthetic data generation |
| `python-dotenv` | 1.0.1 | Loads `.env` file into `os.environ` |
| `httpx` | 0.27.0 | Async HTTP client (used internally by FastAPI test client) |
| `tiktoken` | 0.7.0 | OpenAI tokeniser — used by LangChain to count tokens |
| `reportlab` | 4.2.0 | PDF generation for the synthetic `annual_report_2023.pdf` |
| `sqlalchemy` | 2.0.30 | ORM and connection management for PostgreSQL |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver for SQLAlchemy |

---

## 14. Data & Request Flow (End-to-End)

### Document indexing (upload)

```
User (admin) selects file in browser
    │
    ▼
POST /api/v1/ingest  (multipart/form-data: file + source_type)
    │
    ▼ routes.py
authenticate_user()  →  role must be "admin"
    │
    ▼ ingestion.py → ingest_file()
detect extension  →  select parser
parse file bytes  →  list of text chunks
attach metadata   →  list of Document objects
    │
    ▼ vectorstore.py → add_documents()
embed each chunk  (all-MiniLM-L6-v2, local)
write to ChromaDB (./chroma_db, persistent)
    │
    ▼
return { status, file, source_type, chunks_indexed }
    │
    ▼
Frontend shows success toast: "Indexed N chunks from filename"
```

### Querying (RAG)

```
User types question  →  presses Enter
    │
    ▼
POST /api/v1/query  { query, k=5 }
    │
    ▼ routes.py
authenticate_user()  →  build UserContext (role + allowed_sources)
    │
    ▼ rag_pipeline.py → run_rag_query()
    │
    ├── route_query()
    │       keyword scoring  →  prioritised source list (metadata only)
    │
    ├── rbac_retriever(role, k=5)
    │       ChromaDB similarity search  (where source_type IN [allowed])
    │       Python double-check  (re-filter results)
    │       →  top-5 Document chunks + relevance scores
    │
    ├── format_context()
    │       →  structured context string with source/ref/relevance per chunk
    │
    ├── maybe_query_postgres()  (if analytical + has structured source access)
    │       LLM generates SELECT SQL
    │       run_sql()  executes against Postgres (read-only)
    │       →  live rows appended to context string
    │
    ├── ChatOpenAI.invoke()
    │       system prompt + formatted context + user question
    │       →  raw LLM text (ANSWER / SOURCES USED / CONFIDENCE / REASONING)
    │
    └── parse_llm_response()
            →  { answer, sources_used, confidence, reasoning }
    │
    ▼
return full JSON response
    │
    ▼
Frontend renders chat bubble with answer, citations, confidence badge, chunk viewer
```

---

## 15. Security Model

The system enforces access control at **three independent layers** so that a bug in one layer doesn't expose data:

### Layer 1 — HTTP authentication (routes.py)

Every protected endpoint requires a valid `Authorization: Basic` header. No credentials → HTTP 401 before any business logic runs.

### Layer 2 — ChromaDB where-filter (vectorstore.py)

The vector search query passes `{ "source_type": { "$in": allowed_sources } }` to ChromaDB. The database itself only searches within documents the user is authorised for.

### Layer 3 — Python re-verification (vectorstore.py)

After ChromaDB returns results, every chunk's `source_type` is checked again in Python against `allowed_sources`. Any chunk that slipped through the database filter is dropped. This guards against ChromaDB filter edge cases.

### Layer 4 — LLM prompt instruction

The system prompt explicitly instructs the LLM: *"Never reveal information from sources the user is not authorized to access."* This is a soft control — it guards against prompt injection attacks where a user embeds instructions in their query to try to get the LLM to reveal data from chunks it was shown.

### SQL safety (postgres_source.py)

Text-to-SQL execution checks that the generated SQL starts with `SELECT` before running it. This prevents the LLM from generating `DELETE`, `DROP`, or `UPDATE` statements even if a malicious query attempted to induce it.

---

## 16. User Guide

This section explains how to use the application as an end user. All features are accessible from the web UI at `http://localhost:8000`.

---

### Starting the application

**With Docker (recommended)**

```bash
# Copy the example env file and add your OpenAI key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

docker compose up --build
```

Wait for the log line `Application startup complete.` — the first run takes ~60 seconds because it generates synthetic data and indexes it. Open `http://localhost:8000` in your browser.

**Without Docker**

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

### Signing in

1. Open `http://localhost:8000`.
2. In the left sidebar you will see a **Sign In** section with two fields: **Username** and **Password**.
3. Enter your credentials and click **Connect**, or click any of the **Demo Accounts** quick-login buttons beneath the form.

**Demo accounts available out of the box:**

| Username | Password | Role | Can see |
|---|---|---|---|
| `frank` | `frank123` | admin | Everything — all 8 data sources |
| `alice` | `alice123` | finance | Finance reports, compliance, operational, public |
| `bob` | `bob123` | hr | HR records, compliance, public |
| `carol` | `carol123` | engineering | Engineering docs, operational, public |
| `dave` | `dave123` | legal | Legal contracts, compliance, HR records, public |
| `eve` | `eve123` | sales | Sales data, operational, public |
| `guest` | `guest123` | viewer | Public data only |

Once signed in, the sidebar shows your **name**, **role**, and the **data sources** you are authorised to query. Navigation items for your role appear below.

> **Session persistence:** Your login is saved in the browser's `localStorage`. Refreshing the page does not sign you out. To end your session explicitly, click **Sign out** at the bottom of the sidebar.

---

### Querying the knowledge base

1. After signing in, you land on the **Query Assistant** panel (chat icon in the sidebar).
2. Type your question in the text box at the bottom and press **Enter** (or **Shift+Enter** for a new line, then Enter to send).
3. The system retrieves relevant document chunks from your authorised sources and generates a grounded answer.

**Reading the response:**

| Element | Meaning |
|---|---|
| Answer text | The LLM's response, grounded in indexed documents |
| `◆ High / Medium / Low confidence` badge | How well the retrieved context supported the answer |
| `📄 source_name` badges | Documents the LLM cited in its answer |
| `🔀 N chunks` badge | How many document chunks were retrieved |
| Reasoning block (italic, blue left-border) | Brief explanation of how the answer was derived |
| ▶ Show N retrieved chunks | Click to expand and see the exact text snippets used, with relevance scores |

**Example questions by role:**

- **Finance:** "What was Q1 2024 revenue?", "Which department exceeded budget?"
- **HR:** "How many leave days do employees get?", "What is the performance review cycle?"
- **Engineering:** "What API rate limits apply?", "What are the known platform issues?"
- **Legal:** "What are the payment terms in the Nexus MSA?"
- **Sales:** "What is the MegaCorp deal status?", "Show me the top Q1 deals."
- **Admin:** Any of the above — you can cross-query all sources in one question.

> **Note:** If you ask about data outside your role's authorised sources (e.g. a `viewer` asking about salaries), the system will respond with "Insufficient data in authorized sources" rather than returning restricted content.

---

### Uploading a document

> **Admin only.** Only the `frank` / admin account can upload documents.

1. Sign in as `frank` (or any admin account).
2. Click **Ingest Document** in the left sidebar (upload icon).
3. Select a **Data Source Type** from the dropdown — this determines which users can later query the document:

| Source type | Who can read it after upload |
|---|---|
| `finance_reports` | admin, finance |
| `hr_records` | admin, hr, legal |
| `engineering_docs` | admin, engineering |
| `legal_contracts` | admin, legal |
| `sales_data` | admin, sales |
| `compliance` | admin, finance, hr, legal |
| `operational` | admin, finance, engineering, sales |
| `public` | everyone |

4. Either **drag and drop** a file onto the upload zone, or click the zone to open a file picker. Supported formats: `.pdf`, `.csv`, `.json`, `.jsonl`, `.txt`, `.md`.
5. The selected file's name and size appear below the zone. Click **✕** to deselect and choose a different file.
6. Click **Upload & Index**.
7. A green success message appears showing how many chunks were indexed:
   ```
   ✓ Indexed 42 chunks from quarterly_report.pdf into finance_reports
   ```
   A toast notification confirms success. The document is now immediately queryable.

**If upload fails:**

- A red error message appears with the reason (e.g. unsupported file type, server error).
- Ensure the file extension is one of the supported formats.
- Ensure the server is running and reachable (check the status dot in the top-right corner — green = online).

---

### Viewing the list of indexed documents

> **Admin only.**

1. Sign in as `frank`.
2. Click **Manage Documents** in the left sidebar (folder icon). This nav item is only visible to admin users.
3. The panel loads a table with one row per indexed document:

| Column | Description |
|---|---|
| Document | The source name (filename stem, e.g. `q1_2024_finance_report`) |
| Source Type | The data source category the document was tagged with on upload |
| Chunks | The number of text chunks stored in ChromaDB for this document |
| Action | A Delete button (see below) |

4. Click **Refresh** at the top of the panel to reload the list at any time (e.g. after uploading a new document).

> Documents originating from PostgreSQL tables appear with names like `postgres.employees`, `postgres.sales_deals`, etc. These were indexed via the **Postgres Ingest** feature and can be deleted the same way as file-based documents.

---

### Deleting a document

> **Admin only.**

1. Sign in as `frank`.
2. Navigate to **Manage Documents** in the sidebar.
3. Find the document you want to remove in the table.
4. Click the red **Delete** button on that row.
5. A confirmation dialog appears:
   ```
   Delete all chunks from "quarterly_report"?
   This cannot be undone.
   ```
6. Click **OK** to confirm, or **Cancel** to abort.
7. On success, a toast notification shows how many chunks were removed:
   ```
   Deleted 42 chunks from "quarterly_report"
   ```
   The document disappears from the table immediately.

**What deletion does:**

Deleting a document removes all of its text chunks from ChromaDB. Once deleted:
- The document can no longer be retrieved in any query, for any user.
- The action is permanent — there is no undo. Re-upload the file to restore it.
- The original file on disk (if any) is **not** deleted — only the indexed chunks in the vector store are removed.

---

### Viewing system stats

1. Click **System Stats** in the left sidebar (chart icon).
2. Three cards show at a glance:

| Card | Shows |
|---|---|
| Total Chunks | Total number of indexed chunks across all documents in ChromaDB |
| Your Role | Your role name |
| Collection | The ChromaDB collection name (`enterprise_rag`) |

3. Below the cards, a table lists every data source you are authorised to access, with a short description of what each source contains.

---

### Signing out

Click **Sign out** at the bottom of the left sidebar. This clears your session from both the UI and `localStorage`, so the next browser visit will show the login form again.
