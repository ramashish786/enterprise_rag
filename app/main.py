# app/main.py
# FastAPI application entry point

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up embedding model
    print("Loading embedding model...")
    from app.core.vectorstore import get_embedding_function
    get_embedding_function()
    print("Ready.")
    yield
    print("Shutting down.")


app = FastAPI(
    title="Enterprise RAG Intelligence System",
    description=(
        "Secure, role-aware Retrieval-Augmented Generation across "
        "heterogeneous enterprise data sources with RBAC enforcement."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if DIST_DIR.exists():
    # Serve Vite's hashed JS/CSS bundles
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def root():
        return FileResponse(str(DIST_DIR / "index.html"))

    # Catch-all: return index.html for any non-API path (SPA client-side routing)
    @app.get("/{path:path}")
    def spa_fallback(path: str):
        file = DIST_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(DIST_DIR / "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "service": "Enterprise RAG Intelligence System",
            "docs": "/docs",
            "version": "1.0.0",
        }
