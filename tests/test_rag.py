import pytest
from backend.rag.pipeline import rag_pipeline

@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    # Make sure pipeline is initialized
    rag_pipeline.initialize_pipeline()
    yield

def test_load_documents():
    docs = rag_pipeline.load_documents()
    assert len(docs) > 0
    # Make sure standard policy documents are part of loaded docs
    sources = [doc["metadata"]["source"] for doc in docs]
    assert "credit_policy.txt" in sources
    assert "rbi_guidelines.txt" in sources
    assert "fraud_policy.txt" in sources

def test_retrieve_dti_policy():
    results = rag_pipeline.retrieve("What is the maximum allowed DTI ratio?")
    assert len(results) > 0
    # First result should ideally cite CP-DTI-01 or CP-DTI-02
    citations = [res["citation"] for res in results]
    assert "CP-DTI-01" in citations
    assert any("45%" in res["content"] for res in results)

def test_retrieve_credit_score_policy():
    results = rag_pipeline.retrieve("Underwrite applicant based on credit score")
    assert len(results) > 0
    citations = [res["citation"] for res in results]
    assert "CP-CS-01" in citations
    assert any("750" in res["content"] for res in results)

def test_retrieve_kyc_policy():
    results = rag_pipeline.retrieve("Which documents are accepted for KYC identification?")
    assert len(results) > 0
    citations = [res["citation"] for res in results]
    assert "RBI-KYC-01" in citations
    assert any("Aadhaar" in res["content"] for res in results)

def test_retrieve_fraud_policy():
    results = rag_pipeline.retrieve("Verify document name discrepancies and fraud indicators")
    assert len(results) > 0
    citations = [res["citation"] for res in results]
    assert "FP-DOC-01" in citations
    assert any("discrepancy" in res["content"] for res in results)


def test_crag_grading_and_reformulation_llm_mode():
    from unittest.mock import MagicMock, patch
    from backend.config import settings

    mock_llm_instance = MagicMock()
    mock_response_grader = MagicMock()
    mock_response_grader.content = '{"is_relevant": true, "reasoning": "Matches dti criteria."}'
    
    mock_llm_instance.invoke.return_value = mock_response_grader

    with patch.object(settings, "OPENAI_API_KEY", "sk-test-key-123"):
        with patch("backend.rag.pipeline.ChatOpenAI", return_value=mock_llm_instance):
            # Test grading directly
            is_rel = rag_pipeline.grade_document_relevance("dti limit", "[Clause CP-DTI-01] Stated DTI limits are 40%")
            assert is_rel is True
            assert mock_llm_instance.invoke.call_count == 1


def test_crag_grading_and_reformulation_fallback_mode():
    from unittest.mock import patch
    from backend.config import settings

    # With mock key, should fallback to keyword rules
    with patch.object(settings, "OPENAI_API_KEY", "mock-key-for-development"):
        # Match DTI keyword in content
        is_rel = rag_pipeline.grade_document_relevance("What is the maximum allowed DTI ratio?", "[Clause CP-DTI-01] Stated DTI limits are 40%")
        assert is_rel is True

        # Irrelevant document grading
        is_rel_irrelevant = rag_pipeline.grade_document_relevance("What is the maximum allowed DTI ratio?", "[Clause CP-INC-01] Stated Income limits are 25000")
        assert is_rel_irrelevant is False

        # Reformulated query should follow fallback rules
        expanded = rag_pipeline.reformulate_query("What is the DTI limit?")
        assert "DTI" in expanded
        assert "CP-DTI-01" in expanded

