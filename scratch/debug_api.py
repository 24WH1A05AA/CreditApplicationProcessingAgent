import sys
import os
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# 1. Intake
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
print("CREATE APPLICATION STATUS:", response.status_code)
app_id = response.json().get("application_id")

# Create a dummy file
pan_file = "pan.png"
with open(pan_file, "w") as f:
    f.write("mock content")

try:
    with open(pan_file, "rb") as f:
        files = {"file": ("pan.png", f, "image/png")}
        data = {"document_type": "PAN"}
        response = client.post(f"/applications/{app_id}/documents", data=data, files=files)
        print("UPLOAD STATUS:", response.status_code)
        print("RESPONSE:", response.text)
except Exception as e:
    import traceback
    traceback.print_exc()

if os.path.exists(pan_file):
    os.remove(pan_file)
