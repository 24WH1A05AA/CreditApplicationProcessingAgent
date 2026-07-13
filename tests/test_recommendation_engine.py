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
