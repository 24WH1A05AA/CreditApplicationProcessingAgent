import pytest
from backend.rag.pipeline import rag_pipeline
from backend.tools.policy_engine import CreditPolicyEngine

@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    rag_pipeline.initialize_pipeline()
    yield

def test_evaluate_policy_all_passed():
    # Salaried applicant with good parameters (Credit score 800, DTI 30%, Income 75k, no defaults)
    res = CreditPolicyEngine.evaluate_policy(
        credit_score=800,
        dti_ratio=0.30,
        monthly_income=75000.0,
        has_active_defaults=False
    )
    
    assert len(res.matches) == 4
    assert res.all_passed is True
    assert res.any_failed is False
    assert res.any_refer is False

    # Check citations
    citations = [m.clause_cited for m in res.matches]
    assert "CP-DTI-01" in citations
    assert "CP-CS-01" in citations
    assert "CP-INC-01" in citations
    assert "CP-CS-02" in citations

    # Check status
    assert all(m.status == "PASSED" for m in res.matches)

def test_evaluate_policy_refer_and_fail():
    # Applicant with borderline credit score (680) and high DTI (50% -> FAILED) and defaults (FAILED)
    res = CreditPolicyEngine.evaluate_policy(
        credit_score=680,
        dti_ratio=0.50,
        monthly_income=30000.0,
        has_active_defaults=True
    )
    
    assert res.all_passed is False
    assert res.any_failed is True
    assert res.any_refer is True

    # Find credit score match (should be REFER)
    cs_match = next(m for m in res.matches if m.parameter == "Credit Score")
    assert cs_match.status == "REFER"
    assert "CP-CS-01" in cs_match.clause_cited

    # Find DTI match (should be FAILED)
    dti_match = next(m for m in res.matches if m.parameter == "DTI")
    assert dti_match.status == "FAILED"

    # Find Default match (should be FAILED)
    def_match = next(m for m in res.matches if m.parameter == "Active Defaults")
    assert def_match.status == "FAILED"
