import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.session import SessionLocal
from backend.database.repository import applicant_repo, application_repo, human_decision_repo, audit_log_repo

client = TestClient(app)

@pytest.fixture(name="seeded_application")
def fixture_seeded_application():
    db = SessionLocal()
    # 1. Create a seed applicant
    applicant = applicant_repo.create(db, obj_in={
        "first_name": "Reviewer",
        "last_name": "Test",
        "email": "reviewer.test@example.com",
        "dob": "1988-12-10",
        "monthly_income": 90000.0,
        "existing_emi": 4000.0
    })
    
    # 2. Create a seed application
    application = application_repo.create(db, obj_in={
        "applicant_id": applicant.id,
        "loan_amount": 100000.0,
        "loan_purpose": "Debt Consolidation",
        "status": "PENDING_APPROVAL"
    })
    
    yield application.id
    
    # Teardown
    db.delete(application)
    db.delete(applicant)
    db.commit()
    db.close()

def test_human_approval_api_approve(seeded_application):
    payload = {
        "application_id": seeded_application,
        "decision": "APPROVED",
        "comments": "Approved after document cross-validation. Looks strong.",
        "underwriter_email": "lead.underwriter@techvest.com"
    }

    response = client.post("/approval", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["application_status"] == "APPROVED"
    assert "decision_id" in data

    # Verify database directly
    db = SessionLocal()
    try:
        decisions = human_decision_repo.get_by_application(db, seeded_application)
        assert len(decisions) == 1
        assert decisions[0].decision == "APPROVED"
        assert decisions[0].underwriter_email == "lead.underwriter@techvest.com"
        
        # Verify Audit Log
        logs = audit_log_repo.get_by_application(db, seeded_application)
        assert len(logs) > 0
        actions = [log.action for log in logs]
        assert "HUMAN_APPROVAL" in actions
    finally:
        db.close()

def test_human_approval_api_decline(seeded_application):
    payload = {
        "application_id": seeded_application,
        "decision": "DECLINED",
        "comments": "Declined due to profile mismatch.",
        "underwriter_email": "junior.underwriter@techvest.com"
    }

    response = client.post("/approval", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["application_status"] == "DECLINED"

def test_human_approval_nonexistent_application():
    payload = {
        "application_id": "non-existent-uuid",
        "decision": "APPROVED",
        "comments": "Should fail.",
        "underwriter_email": "underwriter@techvest.com"
    }

    response = client.post("/approval", json=payload)
    assert response.status_code == 404
