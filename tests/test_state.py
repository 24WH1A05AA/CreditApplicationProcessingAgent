import pytest
from backend.agents.state import UnderwritingState

def test_state_instantiation_and_mutability():
    # 1. Initialize State Dict
    state: UnderwritingState = {
        "applicant": {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com",
            "monthly_income": 85000.0,
            "existing_emi": 5000.0,
            "dob": "1988-06-20"
        },
        "documents": [
            {"document_type": "PAN", "file_path": "/data/pan.pdf"},
            {"document_type": "Aadhaar", "file_path": "/data/aadhaar.pdf"}
        ],
        "validation_result": None,
        "retrieved_policy": None,
        "score": None,
        "recommendation": None,
        "fairness_result": None,
        "audit_data": None,
        "human_approval": None,
        "metadata": {}
    }
    
    # 2. Assert values
    assert state["applicant"]["first_name"] == "John"
    assert len(state["documents"]) == 2
    
    # 3. Simulate updates during workflow execution
    state["validation_result"] = {"is_complete": True, "discrepancies": []}
    state["score"] = {"credit_score": 780, "dti_ratio": 0.25, "risk_rating": "LOW"}
    
    assert state["validation_result"]["is_complete"] is True
    assert state["score"]["credit_score"] == 780

def test_state_extensibility():
    # Verify metadata extensibility for future tracking details
    state: UnderwritingState = {
        "applicant": {},
        "documents": [],
        "validation_result": None,
        "retrieved_policy": None,
        "score": None,
        "recommendation": None,
        "fairness_result": None,
        "audit_data": None,
        "human_approval": None,
        "metadata": {}
    }
    
    # Simulate future additions to metadata (like session traces, geographic coordinates, model configs)
    state["metadata"]["session_id"] = "session_abc123"
    state["metadata"]["risk_model_version"] = "v2.4.1"
    state["metadata"]["underwriting_region"] = "APAC"
    
    assert state["metadata"]["session_id"] == "session_abc123"
    assert state["metadata"]["risk_model_version"] == "v2.4.1"
