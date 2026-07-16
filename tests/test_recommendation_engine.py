import pytest
from backend.tools.recommendation_engine import RecommendationEngine

def test_generate_recommendation_approve():
    # Salaried applicant with good parameters
    validation_res = {"is_complete": True, "missing_documents": [], "consistency": {"is_consistent": True, "discrepancies": []}}
    score_res = {"credit_score": 800, "has_active_defaults": False, "dti_ratio": 0.25, "dti_status": "PASSED", "composite_risk_score": 0.0}
    policy_res = {"matches": [{"parameter": "DTI", "clause_cited": "CP-DTI-01", "status": "PASSED", "reasoning": "DTI is within limits."}], "any_failed": False, "any_refer": False}

    reco = RecommendationEngine.generate_recommendation(validation_res, score_res, policy_res)
    assert reco.decision == "APPROVE"
    assert reco.confidence == 0.95
    assert "CP-DTI-01" in reco.policy_citations
    assert len(reco.reasons) > 0

def test_generate_recommendation_refer():
    # Borderline Credit Score
    validation_res = {"is_complete": True, "missing_documents": [], "consistency": {"is_consistent": True, "discrepancies": []}}
    score_res = {"credit_score": 680, "has_active_defaults": False, "dti_ratio": 0.30, "dti_status": "PASSED", "composite_risk_score": 30.0}
    policy_res = {"matches": [{"parameter": "Credit Score", "clause_cited": "CP-CS-01", "status": "REFER", "reasoning": "Score is borderline."}], "any_failed": False, "any_refer": True}

    reco = RecommendationEngine.generate_recommendation(validation_res, score_res, policy_res)
    assert reco.decision == "REFER"
    assert reco.confidence == 0.75
    assert "CP-CS-01" in reco.policy_citations

def test_generate_recommendation_decline():
    # Active default triggers decline
    validation_res = {"is_complete": True, "missing_documents": [], "consistency": {"is_consistent": True, "discrepancies": []}}
    score_res = {"credit_score": 750, "has_active_defaults": True, "dti_ratio": 0.30, "dti_status": "PASSED", "composite_risk_score": 100.0}
    policy_res = {"matches": [{"parameter": "Active Defaults", "clause_cited": "CP-CS-02", "status": "FAILED", "reasoning": "Default reported."}], "any_failed": True, "any_refer": False}

    reco = RecommendationEngine.generate_recommendation(validation_res, score_res, policy_res)
    assert reco.decision == "DECLINE"
    assert reco.confidence == 0.98
    assert "CP-CS-02" in reco.policy_citations


def test_multi_agent_review_loop_success():
    from unittest.mock import MagicMock, patch
    from backend.config import settings

    validation_res = {"is_complete": True, "missing_documents": [], "consistency": {"is_consistent": True, "discrepancies": []}}
    score_res = {"credit_score": 800, "has_active_defaults": False, "dti_ratio": 0.25, "dti_status": "PASSED", "composite_risk_score": 0.0}
    policy_res = {"matches": [], "any_failed": False, "any_refer": False}

    mock_llm_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = """
    {
      "debate_transcript": {
        "doc_auditor": { "vote": "APPROVE", "reasoning": "Documents are valid and complete." },
        "risk_auditor": { "vote": "APPROVE", "reasoning": "Excellent credit score and low DTI ratio." },
        "compliance_auditor": { "vote": "APPROVE", "reasoning": "No compliance overrides triggered." }
      },
      "supervisor_decision": {
        "decision": "APPROVE",
        "reasons": ["Outstanding creditworthiness", "Minor document warning mitigated"],
        "policy_citations": ["CP-CS-01"],
        "confidence": 0.96
      }
    }
    """
    mock_llm_instance.invoke.return_value = mock_response

    with patch.object(settings, "OPENAI_API_KEY", "sk-test-key-123"):
        with patch("backend.tools.recommendation_engine.ChatOpenAI", return_value=mock_llm_instance):
            reco = RecommendationEngine.generate_recommendation(validation_res, score_res, policy_res)
            
            assert reco.decision == "APPROVE"
            assert reco.confidence == 0.96
            assert "CP-CS-01" in reco.policy_citations
            assert any("COMMITTEE DEBATE TRANSCRIPT" in r for r in reco.reasons)
            assert any("SUPERVISOR FINAL RECOMMENDATION" in r for r in reco.reasons)
            assert any("Outstanding creditworthiness" in r for r in reco.reasons)


def test_multi_agent_review_loop_fallback():
    from unittest.mock import patch
    from backend.config import settings

    validation_res = {"is_complete": True, "missing_documents": [], "consistency": {"is_consistent": True, "discrepancies": []}}
    score_res = {"credit_score": 500, "has_active_defaults": False, "dti_ratio": 0.25, "dti_status": "PASSED", "composite_risk_score": 100.0}
    policy_res = {"matches": [], "any_failed": False, "any_refer": False}

    # With mock key, should fallback to rule-based decline
    with patch.object(settings, "OPENAI_API_KEY", "mock-key-for-development"):
        reco = RecommendationEngine.generate_recommendation(validation_res, score_res, policy_res)
        assert reco.decision == "DECLINE"
        assert "COMMITTEE DEBATE TRANSCRIPT" not in "; ".join(reco.reasons)

