import pytest
from fastapi.testclient import TestClient
from backend.main import app
from sqlalchemy.exc import SQLAlchemyError

# Dynamically add test routes to verify global exception handlers
@app.get("/test-error/file-not-found", tags=["Test"])
def trigger_fnf():
    raise FileNotFoundError("Mock missing document file")

@app.get("/test-error/value-error", tags=["Test"])
def trigger_val():
    raise ValueError("Mock invalid format")

@app.get("/test-error/db-error", tags=["Test"])
def trigger_db():
    raise SQLAlchemyError("Mock DB crash")

client = TestClient(app)

def test_file_not_found_handler():
    response = client.get("/test-error/file-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "FILE_NOT_FOUND"
    assert "Mock missing document file" in data["detail"]

def test_value_error_handler():
    response = client.get("/test-error/value-error")
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "VALIDATION_ERROR"
    assert "Mock invalid format" in data["detail"]

def test_db_error_handler():
    response = client.get("/test-error/db-error")
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "DATABASE_ERROR"
    assert "Mock DB crash" in data["detail"]
