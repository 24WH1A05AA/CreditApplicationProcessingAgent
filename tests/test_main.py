import pytest
import os
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.session import SessionLocal
from backend.database.repository import applicant_repo, application_repo

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_complete_rest_api_flow(tmp_path):
    # 1. Test Application Intake
    payload = {
        "loan_amount": 100000.0,
        "loan_purpose": "Home Improvement",
        "applicant": {
            "first_name": "API",
            "last_name": "Tester",
            "email": "api.tester@example.com",
            "dob": "1994-08-20",
            "monthly_income": 60000.0,
            "existing_emi": 2000.0
        }
    }
    
    response = client.post("/applications", json=payload)
    assert response.status_code == 200
    app_data = response.json()
    assert app_data["status"] == "success"
    app_id = app_data["application_id"]
    assert app_id is not None
    
    # 2. Test Document Upload
    pan_file = tmp_path / "pan.png"
    with open(pan_file, "w") as f:
        f.write("mock content")
        
    with open(pan_file, "rb") as f:
        files = {"file": ("pan.png", f, "image/png")}
        data = {"document_type": "PAN"}
        response = client.post(f"/applications/{app_id}/documents", data=data, files=files)
        
    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["status"] == "success"
    assert "document_id" in doc_data
    
    # 3. Test Process Application
    response = client.post(f"/applications/{app_id}/process")
    assert response.status_code == 200
    process_data = response.json()
    assert process_data["status"] == "success"
    assert "recommendation" in process_data
    
    # 4. Test Get Recommendation
    response = client.get(f"/applications/{app_id}/recommendation")
    assert response.status_code == 200
    reco_data = response.json()
    assert reco_data["application_id"] == app_id
    assert "decision" in reco_data
    
    # 5. Test Get Status
    response = client.get(f"/applications/{app_id}")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["id"] == app_id
    assert status_data["loan_amount"] == 100000.0
    assert len(status_data["documents"]) == 1
    
    # Clean up DB
    db = SessionLocal()
    try:
        app_obj = application_repo.get(db, app_id)
        applicant_obj = applicant_repo.get(db, app_obj.applicant_id)
        db.delete(app_obj)
        db.delete(applicant_obj)
        db.commit()
    finally:
        db.close()
