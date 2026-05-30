# app/core/postgres_source.py
# PostgreSQL data source: ingest tables as documents + live text-to-SQL retrieval

import os
import json
from typing import Optional
from sqlalchemy import create_engine, text, inspect
from langchain_core.documents import Document

from app.core.vectorstore import add_documents

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://rag:rag@postgres:5432/enterprise",
)


def get_engine():
    return create_engine(POSTGRES_URL, pool_pre_ping=True)


def list_tables() -> list[str]:
    eng = get_engine()
    insp = inspect(eng)
    return insp.get_table_names()


def get_schema_summary() -> str:
    """Schema description used as context when generating SQL."""
    eng = get_engine()
    insp = inspect(eng)
    parts = []
    for tbl in insp.get_table_names():
        cols = insp.get_columns(tbl)
        col_defs = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        parts.append(f"Table {tbl}({col_defs})")
    return "\n".join(parts)


def ingest_table(
    table_name: str,
    source_type: str,
    limit: int = 1000,
) -> dict:
    eng = get_engine()
    docs = []
    with eng.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT :lim"), {"lim": limit})
        cols = list(result.keys())
        for row_num, row in enumerate(result.mappings(), 1):
            row_text = " | ".join(f"{k}: {row[k]}" for k in cols if row[k] is not None)
            docs.append(Document(
                page_content=row_text,
                metadata={
                    "source_name": f"postgres.{table_name}",
                    "source_type": source_type,
                    "ref": f"row-{row_num}",
                    "file_type": "postgres",
                    "table": table_name,
                },
            ))

    if not docs:
        return {"status": "warning", "message": f"Table {table_name} is empty", "chunks": 0}

    count = add_documents(docs)
    return {
        "status": "success",
        "source": f"postgres.{table_name}",
        "source_type": source_type,
        "chunks_indexed": count,
        "file_type": "postgres",
    }


def run_sql(query: str, max_rows: int = 50) -> list[dict]:
    """
    Execute a read-only SQL query. Raises if not a SELECT.
    Used by text-to-SQL retrieval path.
    """
    q = query.strip().rstrip(";")
    if not q.lower().startswith("select"):
        raise ValueError("Only SELECT queries are permitted")

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(text(q))
        rows = [dict(r) for r in result.mappings().fetchmany(max_rows)]
    return rows


def init_demo_schema():
    """Set up demo tables if they don't exist yet."""
    eng = get_engine()
    ddl = """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT,
        level TEXT,
        annual_salary_usd INTEGER,
        start_date DATE,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS sales_deals (
        deal_id TEXT PRIMARY KEY,
        account TEXT,
        acv_usd INTEGER,
        stage TEXT,
        close_date DATE,
        owner TEXT,
        probability_pct INTEGER
    );

    CREATE TABLE IF NOT EXISTS finance_quarterly (
        quarter TEXT PRIMARY KEY,
        revenue_usd BIGINT,
        opex_usd BIGINT,
        ebitda_usd BIGINT,
        net_profit_usd BIGINT
    );
    """
    seed = [
        ("INSERT INTO employees VALUES ('EMP1001','James Li','Engineering','L3',135000,'2022-04-15','Active') ON CONFLICT DO NOTHING;"),
        ("INSERT INTO employees VALUES ('EMP1002','Maria Garcia','Finance','L4',160000,'2021-08-01','Active') ON CONFLICT DO NOTHING;"),
        ("INSERT INTO employees VALUES ('EMP1003','David Okonkwo','Sales','L3',125000,'2023-01-10','Active') ON CONFLICT DO NOTHING;"),
        ("INSERT INTO employees VALUES ('EMP1004','Priya Patel','HR','L2',95000,'2020-11-20','On Leave') ON CONFLICT DO NOTHING;"),
        ("INSERT INTO employees VALUES ('EMP1005','Tom Andersen','Engineering','L5',195000,'2019-06-05','Active') ON CONFLICT DO NOTHING;"),

        ("INSERT INTO sales_deals VALUES ('DL-001','TechGiant Corp',480000,'Negotiation','2024-03-31','Eve Thompson',75) ON CONFLICT DO NOTHING;"),
        ("INSERT INTO sales_deals VALUES ('DL-002','GlobalBank Ltd',220000,'Proposal','2024-04-15','Eve Thompson',50) ON CONFLICT DO NOTHING;"),
        ("INSERT INTO sales_deals VALUES ('DL-006','MegaCorp',1200000,'Negotiation','2024-06-30','Eve Thompson',65) ON CONFLICT DO NOTHING;"),
        ("INSERT INTO sales_deals VALUES ('DL-004','RetailMax Co',360000,'Closed Won','2024-02-28','Eve Thompson',100) ON CONFLICT DO NOTHING;"),

        ("INSERT INTO finance_quarterly VALUES ('Q1-2024',48700000,31200000,17500000,11800000) ON CONFLICT DO NOTHING;"),
        ("INSERT INTO finance_quarterly VALUES ('Q4-2023',45200000,29800000,15400000,10100000) ON CONFLICT DO NOTHING;"),
        ("INSERT INTO finance_quarterly VALUES ('Q3-2023',42100000,28100000,14000000,9200000) ON CONFLICT DO NOTHING;"),
    ]
    with eng.begin() as conn:
        for stmt in ddl.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        for s in seed:
            conn.execute(text(s))
