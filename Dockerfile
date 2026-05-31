# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build


# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for pypdf, sentence-transformers, reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip + CPU-only PyTorch BEFORE copying requirements.txt so this
# 180 MB layer is cached permanently. Changing requirements.txt will NOT
# re-download torch — only the cheaper pip install -r step reruns.
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Copy the built React app from stage 1
COPY --from=frontend-build /build/dist /app/frontend/dist

# Pre-download embedding model so first request is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

CMD ["sh", "-c", "python scripts/ingest_all.py || true && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
