# tests/test_rag_system.py
# Unit and integration tests for the Enterprise RAG system

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from app.core.rbac import authenticate_user, get_allowed_sources, can_access_source, Role, DataSource
from app.core.ingestion import ingest_text, ingest_csv, ingest_json
from app.core.rag_pipeline import route_query, format_context, parse_llm_response
from langchain_core.documents import Document


# ─── RBAC Tests ───────────────────────────────────────────────────────────────

class TestRBAC:
    def test_authenticate_valid_user(self):
        user = authenticate_user("alice", "alice123")
        assert user is not None
        assert user.username == "alice"
        assert user.role == Role.FINANCE

    def test_authenticate_invalid_password(self):
        user = authenticate_user("alice", "wrongpassword")
        assert user is None

    def test_authenticate_unknown_user(self):
        user = authenticate_user("nonexistent", "pass")
        assert user is None

    def test_finance_cannot_access_hr(self):
        assert not can_access_source(Role.FINANCE, DataSource.HR_RECORDS)

    def test_finance_can_access_finance(self):
        assert can_access_source(Role.FINANCE, DataSource.FINANCE_REPORTS)

    def test_admin_has_all_access(self):
        sources = get_allowed_sources(Role.ADMIN)
        for ds in DataSource:
            assert ds.value in sources

    def test_viewer_only_public(self):
        sources = get_allowed_sources(Role.VIEWER)
        assert sources == [DataSource.PUBLIC]

    def test_hr_cannot_access_finance(self):
        assert not can_access_source(Role.HR, DataSource.FINANCE_REPORTS)

    def test_legal_can_access_hr_records(self):
        # Legal needs HR records for compliance/employment matters
        assert can_access_source(Role.LEGAL, DataSource.HR_RECORDS)


# ─── Ingestion Tests ──────────────────────────────────────────────────────────

class TestIngestion:
    def test_ingest_plain_text(self):
        text = "This is a test document about revenue and budgets.\n" * 20
        docs = ingest_text(text.encode(), "test_doc.txt", "finance_reports")
        assert len(docs) >= 1
        assert docs[0].metadata["source_type"] == "finance_reports"
        assert docs[0].metadata["source_name"] == "test_doc"
        assert docs[0].metadata["file_type"] == "txt"

    def test_ingest_csv(self):
        csv_content = "name,salary,dept\nAlice,90000,Engineering\nBob,85000,Finance\n"
        docs = ingest_csv(csv_content.encode(), "employees.csv", "hr_records")
        assert len(docs) == 2
        assert "Alice" in docs[0].page_content
        assert docs[0].metadata["source_type"] == "hr_records"

    def test_ingest_json_list(self):
        import json
        data = [{"id": 1, "value": "foo"}, {"id": 2, "value": "bar"}]
        json_bytes = json.dumps(data).encode()
        docs = ingest_json(json_bytes, "records.json", "operational")
        assert len(docs) >= 2

    def test_ingest_json_single_object(self):
        import json
        data = {"key": "value", "nested": {"a": 1}}
        json_bytes = json.dumps(data).encode()
        docs = ingest_json(json_bytes, "single.json", "public")
        assert len(docs) >= 1

    def test_metadata_preserved(self):
        text = "Test content for metadata verification."
        docs = ingest_text(text.encode(), "meta_test.txt", "compliance")
        for doc in docs:
            assert "source_name" in doc.metadata
            assert "source_type" in doc.metadata
            assert "ref" in doc.metadata
            assert "file_type" in doc.metadata


# ─── Pipeline / Routing Tests ─────────────────────────────────────────────────

class TestRAGPipeline:
    def test_route_finance_query(self):
        allowed = ["finance_reports", "public", "operational"]
        routed = route_query("What was our Q1 revenue and budget variance?", allowed)
        assert routed[0] == "finance_reports"  # finance should rank first

    def test_route_hr_query(self):
        allowed = ["hr_records", "public", "compliance"]
        routed = route_query("How many annual leave days do employees get?", allowed)
        assert routed[0] == "hr_records"

    def test_route_falls_back_to_all(self):
        allowed = ["finance_reports", "hr_records", "public"]
        routed = route_query("Tell me something", allowed)
        # No strong signal — should return all allowed sources
        assert set(routed) == set(allowed)

    def test_route_only_returns_allowed_sources(self):
        allowed = ["finance_reports", "public"]
        routed = route_query("What is the employee salary?", allowed)
        for source in routed:
            assert source in allowed  # must never return unauthorized source

    def test_format_context_empty(self):
        result = format_context([], [])
        assert "No relevant context" in result

    def test_format_context_with_docs(self):
        docs = [
            Document(
                page_content="Revenue was $48.7M in Q1 2024.",
                metadata={"source_name": "finance_report", "source_type": "finance_reports", "ref": "page-1"},
            )
        ]
        result = format_context(docs, [0.87])
        assert "48.7M" in result
        assert "finance_report" in result
        assert "87" in result  # relevance %

    def test_parse_llm_response_structured(self):
        raw = """ANSWER: Revenue was $48.7M in Q1 2024 [Source: finance_report, Page/Row: page-1].
SOURCES USED: finance_report, department_budgets
CONFIDENCE: High
REASONING: The figure was directly stated in the financial summary section."""
        parsed = parse_llm_response(raw)
        assert "$48.7M" in parsed["answer"]
        assert "finance_report" in parsed["sources_used"]
        assert parsed["confidence"] == "High"
        assert len(parsed["reasoning"]) > 0

    def test_parse_llm_response_fallback(self):
        raw = "Some unstructured response without standard keys."
        parsed = parse_llm_response(raw)
        assert parsed["answer"] == raw
        assert parsed["confidence"] == "Low"


# ─── Security Tests ───────────────────────────────────────────────────────────

class TestSecurity:
    def test_rbac_enforcement_in_retriever(self):
        """Ensure rbac_retriever only returns docs matching allowed sources."""
        from app.core.vectorstore import rbac_retriever
        from app.core.rbac import Role

        # Mock the vectorstore similarity search
        mock_docs = [
            (Document(page_content="Finance data", metadata={"source_type": "finance_reports"}), 0.9),
            (Document(page_content="HR data", metadata={"source_type": "hr_records"}), 0.85),
            (Document(page_content="Public info", metadata={"source_type": "public"}), 0.7),
        ]

        with patch("app.core.vectorstore.get_vectorstore") as mock_vs:
            mock_instance = MagicMock()
            mock_instance.similarity_search_with_relevance_scores.return_value = mock_docs
            mock_vs.return_value = mock_instance

            retrieve = rbac_retriever(Role.FINANCE, k=5)
            docs, scores = retrieve("test query")

            # HR records must be filtered out
            source_types = [d.metadata["source_type"] for d in docs]
            assert "hr_records" not in source_types
            assert "finance_reports" in source_types

    def test_no_privilege_escalation(self):
        """Viewer cannot access any restricted source."""
        assert not can_access_source(Role.VIEWER, DataSource.FINANCE_REPORTS)
        assert not can_access_source(Role.VIEWER, DataSource.HR_RECORDS)
        assert not can_access_source(Role.VIEWER, DataSource.ENGINEERING_DOCS)
        assert not can_access_source(Role.VIEWER, DataSource.LEGAL_CONTRACTS)
        assert not can_access_source(Role.VIEWER, DataSource.SALES_DATA)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
