import sys
import os

# Add project root to path for local execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data

def test_create_application():
    response = client.post("/applications", json={"applicant": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_DOCS"
