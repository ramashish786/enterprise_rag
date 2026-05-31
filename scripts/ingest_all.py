#!/usr/bin/env python3

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from data.synthetic.generate_data import (
    generate_finance_report, generate_finance_csv,
    generate_hr_records, generate_hr_policy,
    generate_engineering_docs, generate_audit_logs,
    generate_legal_doc, generate_sales_data, generate_compliance_doc,
    generate_pdf_report, generate_access_policies, generate_user_role_mappings,
)
from app.core.ingestion import ingest_file

DATA_DIR = Path("data/synthetic")

# Sentinel file lives inside the chroma_data named volume.
# Its presence means ingestion already ran successfully.
# It is wiped only when the volume is deleted (docker compose down -v).
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))
SENTINEL = CHROMA_DIR / ".ingestion_complete"

FILE_SOURCE_MAP = {
    "q1_2024_finance_report.txt": "finance_reports",
    "department_budgets_q1_2024.csv": "finance_reports",
    "annual_report_2023.pdf": "finance_reports",
    "employee_records.json": "hr_records",
    "hr_policy_manual.txt": "hr_records",
    "platform_architecture.txt": "engineering_docs",
    "audit_trail.json": "compliance",
    "msa_nexus_ventures_2024.txt": "legal_contracts",
    "sales_pipeline_q1_2024.csv": "sales_data",
    "compliance_policy.txt": "compliance",
    "access_policies.json": "compliance",
    "user_role_mappings.csv": "public",
}


def main():
    print("=" * 60)
    print("  Enterprise RAG — Data Ingestion Pipeline")
    print("=" * 60)

    # Always ensure Postgres schema and seed data exist (ON CONFLICT DO NOTHING makes this safe)
    print("\n[0/3] Ensuring PostgreSQL schema...")
    try:
        from app.core.postgres_source import init_demo_schema
        init_demo_schema()
        print("  ✓ Postgres schema ready")
    except Exception as e:
        print(f"  ⚠ Postgres unavailable, skipping: {e}")

    # Sentinel check — skip if ingestion already completed on a previous run.
    # The sentinel lives inside the chroma_data volume so it survives restarts
    # and is only removed when the volume itself is deleted.
    if SENTINEL.exists():
        print("\n✓ Ingestion already complete (sentinel found) — skipping.")
        print("  To re-ingest from scratch: docker compose down -v && docker compose up")
        return

    print("\n[1/3] Generating synthetic datasets...")
    generate_finance_report()
    generate_finance_csv()
    generate_hr_records()
    generate_hr_policy()
    generate_engineering_docs()
    generate_audit_logs()
    generate_legal_doc()
    generate_sales_data()
    generate_compliance_doc()
    generate_pdf_report()
    generate_access_policies()
    generate_user_role_mappings()

    # Ingest Postgres tables into ChromaDB
    print("\n[2/3] Indexing PostgreSQL tables into ChromaDB...")
    try:
        from app.core.postgres_source import ingest_table
        pg_tables = {
            "employees": "hr_records",
            "sales_deals": "sales_data",
            "finance_quarterly": "finance_reports",
        }
        for tbl, src_type in pg_tables.items():
            try:
                r = ingest_table(tbl, src_type)
                print(f"  ✓ postgres.{tbl:25s} → {src_type:20s} ({r.get('chunks_indexed', 0)} rows)")
            except Exception as e:
                print(f"  ✗ postgres.{tbl}: {e}")
    except Exception as e:
        print(f"  ⚠ Postgres unavailable, skipping: {e}")

    print("\n[3/3] Indexing files into ChromaDB...")
    total_chunks = 0
    errors = []
    for filename, source_type in FILE_SOURCE_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  ⚠ SKIP  {filename} (not found)")
            continue
        with open(filepath, "rb") as f:
            file_bytes = f.read()
        try:
            result = ingest_file(file_bytes, filename, source_type)
            chunks = result.get("chunks_indexed", 0)
            total_chunks += chunks
            print(f"  ✓ {filename:42s} → {source_type:20s} ({chunks} chunks)")
        except Exception as e:
            errors.append(f"{filename}: {e}")
            print(f"  ✗ {filename}: {e}")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()

    print(f"\n{'=' * 60}")
    print(f"  Done! {total_chunks} chunks indexed.")
    if errors:
        print(f"  {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
