import pytest
import os
from backend.agents.state import UnderwritingState
from backend.agents.nodes import WorkflowNodes
from backend.rag.pipeline import rag_pipeline
from backend.database.session import SessionLocal

@pytest.fixture(scope="module", autouse=True)
def setup_dependencies():
    # Make sure RAG pipeline is initialized
    rag_pipeline.initialize_pipeline()
    yield

def test_nodes_sequential_execution(tmp_path):
    # Setup mock document files
    pan_path = tmp_path / "mock_pan.png"
    aadhaar_path = tmp_path / "mock_aadhaar.jpg"
    with open(pan_path, "w") as f:
        f.write("")
    with open(aadhaar_path, "w") as f:
        f.write("")

    # Initialize State
    state: UnderwritingState = {
        "applicant": {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "clear.approve@example.com",
            "phone": "9876543210",
            "dob": "1990-05-15",
            "monthly_income": 80000.0,
            "existing_emi": 5000.0,
            "loan_amount": 150000.0
        },
        "documents": [
            {"document_type": "PAN", "file_path": str(pan_path)},
            {"document_type": "Aadhaar", "file_path": str(aadhaar_path)}
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

    # 1. Execute Loan Intake Node
    intake_update = WorkflowNodes.loan_intake(state)
    assert intake_update["applicant"]["id"] is not None
    assert intake_update["applicant"]["application_id"] is not None
    state.update(intake_update)

    # 2. Execute Document Validation Node
    validation_update = WorkflowNodes.document_validation(state)
    assert "pan" in validation_update["validation_result"]
    assert "aadhaar" in validation_update["validation_result"]
    assert validation_update["validation_result"]["is_complete"] is False  # Missing Salary/Bank statements
    state.update(validation_update)

    # 3. Execute Credit Scoring Node
    score_update = WorkflowNodes.credit_scoring(state)
    assert score_update["score"]["credit_score"] == 800
    assert score_update["score"]["risk_rating"] == "LOW"
    state.update(score_update)

    # 4. Execute Policy Retrieval Node
    policy_update = WorkflowNodes.policy_retrieval(state)
    assert len(policy_update["retrieved_policy"]["matches"]) == 4
    state.update(policy_update)

    # 5. Execute Recommendation Node
    reco_update = WorkflowNodes.recommendation(state)
    # Since documents were incomplete (missing salary/bank statements), should be DECLINE or REFER
    assert reco_update["recommendation"]["decision"] in ["DECLINE", "REFER"]
    state.update(reco_update)

    # 6. Execute Fairness Check Node
    fairness_update = WorkflowNodes.fairness_check(state)
    assert fairness_update["fairness_result"]["is_fair"] is True
    state.update(fairness_update)

    # 7. Execute Human Approval Node
    human_update = WorkflowNodes.human_approval(state)
    assert human_update["human_approval"]["status"] in ["PENDING_REVIEW", "AUTO_PROCESSED"]
    state.update(human_update)

    # 8. Execute Audit Logging Node
    audit_update = WorkflowNodes.audit_logging(state)
    assert audit_update["audit_data"]["log_id"] is not None
    state.update(audit_update)
