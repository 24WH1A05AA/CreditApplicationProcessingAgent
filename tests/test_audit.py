import pytest
import os
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.session import SessionLocal
from backend.database.repository import applicant_repo, application_repo, audit_log_repo
from backend.agents.workflow import run_underwriting_workflow
from backend.agents.state import UnderwritingState
from backend.rag.pipeline import rag_pipeline

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    rag_pipeline.initialize_pipeline()
    yield

def test_audit_trail_generation_and_query(tmp_path):
    # Setup mock files
    pan = tmp_path / "mock_pan.png"
    aadhaar = tmp_path / "mock_aadhaar.jpg"
    with open(pan, "w") as f:
        f.write("")
    with open(aadhaar, "w") as f:
        f.write("")

    # Run workflow to produce audit trails
    state: UnderwritingState = {
        "applicant": {
            "first_name": "Traceable",
            "last_name": "Applicant",
            "email": "clear.approve@example.com",
            "phone": "9998887776",
            "dob": "1992-04-12",
            "monthly_income": 99000.0,
            "existing_emi": 5000.0,
            "loan_amount": 250000.0
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

    final_state = run_underwriting_workflow(state)
    app_id = final_state["applicant"]["application_id"]
    assert app_id is not None

    # Query API endpoint for audit logs
    response = client.get(f"/audit/{app_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["application_id"] == app_id
    assert len(data["logs"]) > 0

    # Inspect execution trace log
    wf_log = next(log for log in data["logs"] if log["action"] == "WORKFLOW_EXECUTION")
    assert wf_log["performed_by"] == "LANGGRAPH_ENGINE"
    
    details = wf_log["details"]
    assert "applicant" in details
    assert "validation_result" in details
    assert "retrieved_policy" in details
    assert "score" in details
    assert "recommendation" in details
    assert "tool_calls" in details
    assert "FairnessChecker" in details["tool_calls"]
    
    # Verify directly via repo
    db = SessionLocal()
    try:
        db_logs = audit_log_repo.get_by_application(db, app_id)
        assert len(db_logs) > 0
    finally:
        db.close()
