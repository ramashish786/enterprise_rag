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
├── Dockerfile                   ← Multi-stage: Node (React build) → Python (API)
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── app/
│   ├── main.py                  ← FastAPI entry + serves frontend/dist/
│   ├── api/routes.py            ← /query, /ingest, /documents, /me, /postgres/*
│   └── core/
│       ├── rbac.py              ← Roles + permissions + auth
│       ├── vectorstore.py       ← ChromaDB + RBAC retriever + list/delete docs
│       ├── ingestion.py         ← PDF / CSV / JSON / TXT loaders
│       ├── postgres_source.py   ← Postgres schema, ingest, text-to-SQL
│       └── rag_pipeline.py      ← Routing → retrieval → generation
├── frontend/
│   ├── package.json             ← React + Vite
│   ├── vite.config.js           ← Build config + /api proxy for local dev
│   ├── index.html               ← Vite HTML shell
│   └── src/
│       ├── main.jsx             ← React root
│       ├── App.jsx              ← Layout, panel routing, server status
│       ├── api.js               ← apiFetch() with auth headers
│       ├── constants.js         ← Demo users, source descriptions, example queries
│       ├── index.css            ← Global dark-theme styles
│       ├── contexts/
│       │   ├── AuthContext.jsx  ← Session state, login/logout, localStorage restore
│       │   └── ToastContext.jsx ← Toast notification system
│       └── components/
│           ├── Sidebar.jsx      ← Logo, login/nav, sign-out
│           ├── LoginCard.jsx    ← Username/password form
│           ├── UserPill.jsx     ← Logged-in user badge
│           ├── DemoUsers.jsx    ← Quick-login demo account pills
│           └── panels/
│               ├── QueryPanel.jsx   ← Chat interface + chunk viewer
│               ├── IngestPanel.jsx  ← Drag-drop file upload (admin)
│               ├── DocsPanel.jsx    ← Document list + delete (admin)
│               └── StatsPanel.jsx   ← Stats cards + authorized sources
├── data/synthetic/generate_data.py
├── scripts/ingest_all.py        ← Generate + index all data (sentinel-guarded)
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
docker compose up --build -d
```

This starts **two containers**:
- `rag-postgres` — PostgreSQL 16 with seeded enterprise tables
- `enterprise-rag` — FastAPI app + ChromaDB + React frontend

The build has two stages: first Node.js compiles the React app into `frontend/dist/`, then Python installs dependencies and pre-downloads the embedding model.

On first start (~90 sec):
1. Postgres initialises the database
2. App generates 12 synthetic data files
3. Indexes everything into ChromaDB (sentinel file written — skipped on future restarts)
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

## Using the App

### Signing in

Open **http://localhost:8000** in your browser.

**Option A — Quick login (demo accounts)**

Click any user pill in the sidebar under **Demo Accounts**. It auto-fills the credentials and logs you in immediately.

**Option B — Manual login**

1. Enter a username and password in the **Sign In** fields.
2. Click **Connect**.

Once signed in, the sidebar shows your name, role, and the data sources you are authorised to access. Your session is saved in the browser so **refreshing the page does not log you out**. To end the session click **Sign out** at the bottom of the sidebar.

---

### Querying the knowledge base

1. After login you land on the **Query Assistant** panel (chat icon).
2. Type a question in the text box and press **Enter** to send (use **Shift + Enter** for a new line).
3. The answer appears as a chat bubble with:

| Element | What it means |
|---|---|
| Answer text | LLM response grounded in your authorised documents |
| `◆ High / Medium / Low` badge | Confidence based on how well the retrieved context matched the question |
| `📄 source_name` badges | Documents cited in the answer |
| `🔀 N chunks` badge | Number of document chunks retrieved |
| Reasoning block *(italic, blue border)* | Brief explanation of how the answer was derived |
| ▶ Show N retrieved chunks | Click to expand and inspect the exact text snippets used, with relevance % scores |

> **RBAC in action:** If you ask about data outside your role (e.g. a `viewer` asking about salaries), the system returns *"Insufficient data in authorized sources"* — it never leaks restricted content.

---

### Uploading a document *(admin only)*

> Only the **frank / admin** account can upload documents. The **Ingest Document** option is hidden from all other roles.

1. Sign in as `frank` (`frank123`).
2. Click **Ingest Document** in the sidebar (upload icon).
3. Choose a **Data Source Type** from the dropdown. This controls which roles can query the document after upload:

| Source type | Roles that can read it |
|---|---|
| `finance_reports` | admin, finance |
| `hr_records` | admin, hr, legal |
| `engineering_docs` | admin, engineering |
| `legal_contracts` | admin, legal |
| `sales_data` | admin, sales |
| `compliance` | admin, finance, hr, legal |
| `operational` | admin, finance, engineering, sales |
| `public` | everyone |

4. **Drag and drop** a file onto the upload zone, or click it to open a file picker.
   Supported formats: `.pdf` `.csv` `.json` `.jsonl` `.txt` `.md`
5. The selected file name and size appear below the zone. Click **✕** to deselect.
6. Click **Upload & Index**.
7. A green confirmation shows how many chunks were indexed:
   ```
   ✓ Indexed 42 chunks from quarterly_report.pdf into finance_reports
   ```
   The document is immediately queryable by authorised users.

---

### Viewing the list of indexed documents *(admin only)*

> The **Manage Documents** panel is visible only to the admin role.

1. Sign in as `frank`.
2. Click **Manage Documents** in the sidebar (folder icon).
3. A table loads with one row per indexed document:

| Column | Description |
|---|---|
| Document | Source name (filename stem, e.g. `q1_2024_finance_report`) |
| Source Type | Data source category the document was tagged with |
| Chunks | Number of text chunks stored in ChromaDB for this document |
| Action | Delete button (see below) |

4. Click **Refresh** at any time to reload the list (e.g. after uploading a new file).

> Documents indexed from PostgreSQL tables appear as `postgres.employees`, `postgres.sales_deals`, etc. They can be deleted the same way as file-based documents.

---

### Deleting a document *(admin only)*

1. Sign in as `frank`.
2. Open **Manage Documents** in the sidebar.
3. Find the document you want to remove and click its red **Delete** button.
4. A confirmation dialog appears — click **OK** to confirm or **Cancel** to abort.
5. On success a toast notification shows:
   ```
   Deleted 42 chunks from "quarterly_report"
   ```
   The document disappears from the table and is no longer retrievable in any query.

> **Note:** Deletion removes all chunks from ChromaDB permanently. It does **not** delete the original file from disk. To restore a deleted document, re-upload it via **Ingest Document**.

---

### Viewing system stats

Click **System Stats** in the sidebar (chart icon) to see:

| Card | Shows |
|---|---|
| Total Chunks | All chunks indexed in ChromaDB (system-wide) |
| Your Role | Your current role |
| Collection | ChromaDB collection name (`enterprise_rag`) |

Below the cards, the **Your Authorized Sources** table lists every data source your role can access, with a short description of each.

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
| GET | `/api/v1/documents` | Admin | List all indexed documents with chunk counts |
| DELETE | `/api/v1/documents/{source_name}` | Admin | Delete all chunks for a document |
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

## Development Workflow

| What changed | Command needed |
|---|---|
| Python backend code (`app/`) | Nothing — uvicorn `--reload` picks it up automatically |
| Frontend React code (`frontend/src/`) | `docker compose up --build -d` OR run Vite dev server locally (see below) |
| `requirements.txt` or `Dockerfile` | `docker compose up --build -d` |
| Wipe all data and re-ingest from scratch | `docker compose down -v && docker compose up --build -d` |

### Local frontend development (hot module replacement)

Run the Vite dev server alongside the Docker backend for instant React updates:

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173 (proxies /api/* to localhost:8000)
```

The `vite.config.js` proxy forwards all `/api` calls to the FastAPI backend running in Docker, so you get HMR for UI changes without touching the backend.

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

# 4. Build the React frontend
cd frontend && npm install && npm run build && cd ..

# 5. Generate data & index
python scripts/ingest_all.py

# 6. Start server
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
| `OPENAI_API_KEY` not set | Edit `.env`, restart with `docker compose up -d` |
| Postgres connection refused | Wait 30 s — health check gates the app on Postgres readiness |
| Embedding model download slow on first build | Normal — `all-MiniLM-L6-v2` (~90 MB) is cached in the image layer after first `--build` |
| Frontend shows offline (red dot) | Backend still starting; refresh after ~90 s |
| Empty answers / no chunks | Delete the sentinel and re-ingest: `docker compose down -v && docker compose up --build -d` |
| Ingestion runs on every restart | Sentinel file (`chroma_db/.ingestion_complete`) should exist; if missing, run `docker compose up --build -d` once |
| Frontend not updating after UI change | React is built into the image; run `docker compose up --build -d` or use `npm run dev` locally |
| ChromaDB telemetry errors in logs | Already suppressed via `ANONYMIZED_TELEMETRY=False` env var |
| LangChain deprecation warnings | Already fixed — using `langchain-huggingface` package |
| Rebuild from scratch | `docker compose down -v && docker compose up --build -d` |


## Snap of Project
![alt text](images/img_01.png)
![alt text](images/img_02.png)
