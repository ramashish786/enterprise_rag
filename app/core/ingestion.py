# app/core/ingestion.py
# Multi-format document ingestion: PDF, CSV, JSON, TXT

import json
import csv
import io
import os
from pathlib import Path
from typing import Union

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.vectorstore import add_documents

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _make_doc(text: str, metadata: dict) -> Document:
    return Document(page_content=text.strip(), metadata=metadata)


def ingest_pdf(file_bytes: bytes, source_name: str, source_type: str) -> list[Document]:
    reader = PdfReader(io.BytesIO(file_bytes))
    docs = []
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            docs.append(_make_doc(chunk, {
                "source_name": source_name,
                "source_type": source_type,
                "ref": f"page-{page_num}-chunk-{i+1}",
                "file_type": "pdf",
            }))
    return docs


def ingest_csv(file_bytes: bytes, source_name: str, source_type: str) -> list[Document]:
    text = file_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    docs = []
    for row_num, row in enumerate(reader, 1):
        row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
        if not row_text.strip():
            continue
        docs.append(_make_doc(row_text, {
            "source_name": source_name,
            "source_type": source_type,
            "ref": f"row-{row_num}",
            "file_type": "csv",
        }))
    return docs


def ingest_json(file_bytes: bytes, source_name: str, source_type: str) -> list[Document]:
    text = file_bytes.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Treat as NDJSON (one JSON object per line)
        data = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except Exception:
                    pass

    docs = []
    items = data if isinstance(data, list) else [data]
    for i, item in enumerate(items, 1):
        item_text = json.dumps(item, indent=2) if isinstance(item, dict) else str(item)
        chunks = splitter.split_text(item_text)
        for j, chunk in enumerate(chunks):
            docs.append(_make_doc(chunk, {
                "source_name": source_name,
                "source_type": source_type,
                "ref": f"record-{i}-chunk-{j+1}",
                "file_type": "json",
            }))
    return docs


def ingest_text(file_bytes: bytes, source_name: str, source_type: str) -> list[Document]:
    text = file_bytes.decode("utf-8", errors="replace")
    chunks = splitter.split_text(text)
    docs = []
    for i, chunk in enumerate(chunks, 1):
        docs.append(_make_doc(chunk, {
            "source_name": source_name,
            "source_type": source_type,
            "ref": f"chunk-{i}",
            "file_type": "txt",
        }))
    return docs


INGESTOR_MAP = {
    ".pdf": ingest_pdf,
    ".csv": ingest_csv,
    ".json": ingest_json,
    ".jsonl": ingest_json,
    ".txt": ingest_text,
    ".md": ingest_text,
}


def ingest_file(
    file_bytes: bytes,
    filename: str,
    source_type: str,
) -> dict:
    """
    Main entry point: detect format, parse, chunk, and index into ChromaDB.
    Returns a summary dict.
    """
    ext = Path(filename).suffix.lower()
    ingestor = INGESTOR_MAP.get(ext)
    if not ingestor:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(INGESTOR_MAP)}")

    source_name = Path(filename).stem
    docs = ingestor(file_bytes, source_name, source_type)
    if not docs:
        return {"status": "warning", "message": "No content extracted", "chunks": 0}

    count = add_documents(docs)
    return {
        "status": "success",
        "file": filename,
        "source_type": source_type,
        "chunks_indexed": count,
        "file_type": ext,
    }


def ingest_directory(dir_path: str, source_type: str) -> list[dict]:
    """Batch ingest all supported files in a directory."""
    results = []
    for filepath in Path(dir_path).rglob("*"):
        if filepath.suffix.lower() in INGESTOR_MAP:
            with open(filepath, "rb") as f:
                file_bytes = f.read()
            try:
                result = ingest_file(file_bytes, filepath.name, source_type)
            except Exception as e:
                result = {"status": "error", "file": filepath.name, "error": str(e)}
            results.append(result)
    return results
