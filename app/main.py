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

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def root():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "service": "Enterprise RAG Intelligence System",
            "docs": "/docs",
            "version": "1.0.0",
        }
