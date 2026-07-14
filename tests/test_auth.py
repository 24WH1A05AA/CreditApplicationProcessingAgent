import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.session import SessionLocal, engine, Base
from backend.database.repository import user_repo

# Ensure tables are created for testing
Base.metadata.create_all(bind=engine)

def test_auth_flow():
    with TestClient(app) as client:
        # 1. Register a new user
        reg_payload = {
            "username": "auth_test_user",
            "password": "secure_password",
            "role": "UNDERWRITER"
        }
        response = client.post("/auth/register", json=reg_payload)
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "auth_test_user"
        assert user_data["role"] == "UNDERWRITER"
        assert "id" in user_data

        # 2. Try registering the same username again (should fail)
        response = client.post("/auth/register", json=reg_payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already registered"

        # 3. Login to get a token
        login_payload = {
            "username": "auth_test_user",
            "password": "secure_password"
        }
        response = client.post("/auth/token", data=login_payload)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        # 4. Login with wrong password (should fail)
        bad_login_payload = {
            "username": "auth_test_user",
            "password": "wrong_password"
        }
        response = client.post("/auth/token", data=bad_login_payload)
        assert response.status_code == 401

        # 5. Access route requiring UNDERWRITER/ADMIN using the token
        headers = {"Authorization": f"Bearer {token}"}
        app_payload = {
            "loan_amount": 50000.0,
            "loan_purpose": "Debt Consolidation",
            "applicant": {
                "first_name": "Auth",
                "last_name": "User",
                "email": "auth.user@example.com",
                "dob": "1990-01-01",
                "monthly_income": 80000.0,
                "existing_emi": 5000.0
            }
        }
        response = client.post("/applications", json=app_payload, headers=headers)
        assert response.status_code == 200
        app_data = response.json()
        assert app_data["status"] == "success"
        app_id = app_data["application_id"]

        # 6. Register a restricted user (AUDITOR)
        auditor_payload = {
            "username": "auth_auditor_user",
            "password": "secure_password",
            "role": "AUDITOR"
        }
        response = client.post("/auth/register", json=auditor_payload)
        assert response.status_code == 200
        
        # Login auditor
        response = client.post("/auth/token", data={"username": "auth_auditor_user", "password": "secure_password"})
        assert response.status_code == 200
        auditor_token = response.json()["access_token"]
        auditor_headers = {"Authorization": f"Bearer {auditor_token}"}

        # Try creating application with AUDITOR token (should fail with 403 Forbidden)
        response = client.post("/applications", json=app_payload, headers=auditor_headers)
        assert response.status_code == 403

        # Try getting audit log with AUDITOR token (should succeed)
        response = client.get(f"/audit/{app_id}", headers=auditor_headers)
        assert response.status_code == 200

        # Try getting audit log with UNDERWRITER token (should fail with 403 Forbidden)
        response = client.get(f"/audit/{app_id}", headers=headers)
        assert response.status_code == 403

        # Clean up DB users and application
        db = SessionLocal()
        try:
            from backend.database.repository import applicant_repo, application_repo
            app_obj = application_repo.get(db, app_id)
            if app_obj:
                applicant_obj = applicant_repo.get(db, app_obj.applicant_id)
                db.delete(app_obj)
                if applicant_obj:
                    db.delete(applicant_obj)
            
            user1 = user_repo.get_by_username(db, "auth_test_user")
            if user1:
                db.delete(user1)
            user2 = user_repo.get_by_username(db, "auth_auditor_user")
            if user2:
                db.delete(user2)
            db.commit()
        finally:
            db.close()

