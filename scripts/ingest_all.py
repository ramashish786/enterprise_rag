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

    print("\n[1/2] Generating synthetic datasets...")
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

    # Initialise & ingest Postgres tables
    print("\n[1.5/2] Setting up PostgreSQL data source...")
    try:
        from app.core.postgres_source import init_demo_schema, ingest_table, list_tables
        init_demo_schema()
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

    print("\n[2/2] Indexing into ChromaDB...")
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

    print(f"\n{'=' * 60}")
    print(f"  Done! {total_chunks} total chunks indexed.")
    if errors:
        print(f"  {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
