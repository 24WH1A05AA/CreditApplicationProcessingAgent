import pytest
import os
from backend.agents.state import UnderwritingState
from backend.agents.workflow import run_underwriting_workflow, underwriting_workflow
from backend.rag.pipeline import rag_pipeline

@pytest.fixture(scope="module", autouse=True)
def setup_dependencies():
    rag_pipeline.initialize_pipeline()
    yield

def test_workflow_compilation():
    assert underwriting_workflow is not None

def test_workflow_end_to_end_execution(tmp_path):
    # Create mock document files
    pan = tmp_path / "mock_pan.png"
    aadhaar = tmp_path / "mock_aadhaar.jpg"
    with open(pan, "w") as f:
        f.write("")
    with open(aadhaar, "w") as f:
        f.write("")

    initial_state: UnderwritingState = {
        "applicant": {
            "first_name": "James",
            "last_name": "Smith",
            "email": "clear.approve@example.com",
            "phone": "9999988888",
            "dob": "1985-08-10",
            "monthly_income": 95000.0,
            "existing_emi": 8000.0,
            "loan_amount": 200000.0
        },
        "documents": [
            {"document_type": "PAN", "file_path": str(pan)},
            {"document_type": "Aadhaar", "file_path": str(aadhaar)}
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

    # Run the compiled graph end-to-end
    final_state = run_underwriting_workflow(initial_state)

    # Assert all keys are populated during graph traversal
    assert final_state["metadata"].get("intake_completed") is True
    assert final_state["validation_result"] is not None
    assert final_state["score"] is not None
    assert final_state["retrieved_policy"] is not None
    assert final_state["recommendation"] is not None
    assert final_state["fairness_result"] is not None
    assert final_state["human_approval"] is not None
    assert final_state["audit_data"] is not None

def test_workflow_graceful_failure():
    # Pass invalid applicant details that trigger database exceptions during intake node
    bad_state: UnderwritingState = {
        "applicant": {
            "email": None  # Will throw integrity error as email is non-nullable key
        },
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

    result = run_underwriting_workflow(bad_state)
    assert result["metadata"].get("workflow_status") == "FAILED"
    assert "workflow_execution_error" in result["metadata"]
