# app/core/vectorstore.py
# ChromaDB vector store setup with role-aware retrieval

import os
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document

from app.core.rbac import get_allowed_sources

COLLECTION_NAME = "enterprise_rag"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


def get_embedding_function():
    return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")


def get_chroma_client() -> chromadb.PersistentClient:
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_vectorstore() -> Chroma:
    embeddings = get_embedding_function()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )


def add_documents(documents: list[Document]) -> int:
    """Index a list of LangChain Documents into ChromaDB."""
    vs = get_vectorstore()
    vs.add_documents(documents)
    return len(documents)


def rbac_retriever(role: str, k: int = 5):
    """
    Returns a callable retriever that filters results by the user's
    allowed data sources before returning chunks.
    """
    allowed = get_allowed_sources(role)
    vs = get_vectorstore()

    def retrieve(query: str) -> list[Document]:
        # ChromaDB where filter: source must be in allowed list
        where_filter = {"source_type": {"$in": allowed}}
        results = vs.similarity_search_with_relevance_scores(
            query,
            k=k * 2,  # over-fetch then filter for safety
            filter=where_filter,
        )
        # secondary guard — chroma filters aren't guaranteed to be exhaustive
        safe_results = [
            (doc, score)
            for doc, score in results
            if doc.metadata.get("source_type") in allowed
        ]
        safe_results.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in safe_results[:k]], [score for _, score in safe_results[:k]]

    return retrieve


def collection_stats() -> dict:
    client = get_chroma_client()
    try:
        col = client.get_collection(COLLECTION_NAME)
        return {"total_documents": col.count(), "collection": COLLECTION_NAME}
    except Exception:
        return {"total_documents": 0, "collection": COLLECTION_NAME}
