import pytest
import os
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.agents.workflow import run_underwriting_workflow
from backend.agents.state import UnderwritingState
from backend.rag.pipeline import rag_pipeline
from backend.utils.observability import ObservabilityManager

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    rag_pipeline.initialize_pipeline()
    yield

def test_observability_workflow_tracing(tmp_path):
    # Setup mock files
    pan = tmp_path / "mock_pan.png"
    aadhaar = tmp_path / "mock_aadhaar.jpg"
    with open(pan, "w") as f:
        f.write("")
    with open(aadhaar, "w") as f:
        f.write("")

    # Run workflow
    state: UnderwritingState = {
        "applicant": {
            "first_name": "Observed",
            "last_name": "User",
            "email": "clear.approve@example.com",
            "phone": "9998887776",
            "dob": "1992-05-15",
            "monthly_income": 80000.0,
            "existing_emi": 5000.0,
            "loan_amount": 150000.0
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
    
    # Assert metadata contains timings and token usage
    meta = final_state.get("metadata", {})
    assert "node_timings" in meta
    assert "execution_path" in meta
    assert "token_usage" in meta
    
    assert "loan_intake_node" in meta["node_timings"]
    assert "audit_logging_node" in meta["node_timings"]
    assert "loan_intake_node" in meta["execution_path"]

    # Verify a debug trace file was stored on disk
    traces = os.listdir("./data/debug_traces")
    matching_traces = [t for t in traces if app_id in t]
    assert len(matching_traces) > 0

    trace_file_path = os.path.join("./data/debug_traces", matching_traces[0])
    with open(trace_file_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)
    assert trace_data["applicant"]["email"] == "clear.approve@example.com"
    assert "metadata" in trace_data

    # Test the API endpoint for observability
    response = client.get(f"/applications/{app_id}/observability")
    assert response.status_code == 200
    obs_res = response.json()
    assert obs_res["application_id"] == app_id
    assert "mermaid_chart" in obs_res
    assert "graph TD" in obs_res["mermaid_chart"]
    assert "loan_intake_node" in obs_res["execution_path"]
    assert obs_res["total_latency_ms"] > 0
