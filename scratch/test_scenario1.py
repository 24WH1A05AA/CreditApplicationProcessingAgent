import os
from unittest.mock import patch
from backend.database.session import SessionLocal, Base, engine
from backend.rag.pipeline import rag_pipeline
from backend.agents.workflow import run_underwriting_workflow
from backend.tools.ocr_processor import OCRProcessor

# Initialize
rag_pipeline.initialize_pipeline()
Base.metadata.create_all(bind=engine)

# Create temp docs
tmp_dir = "./temp_test_sc1"
os.makedirs(tmp_dir, exist_ok=True)
docs = [
    {"document_type": "PAN", "file_path": os.path.join(tmp_dir, "pan.png")},
    {"document_type": "Aadhaar", "file_path": os.path.join(tmp_dir, "aadhaar.png")},
    {"document_type": "Salary Slip", "file_path": os.path.join(tmp_dir, "salary_slip.png")},
    {"document_type": "Bank Statement", "file_path": os.path.join(tmp_dir, "bank_statement.png")}
]
for d in docs:
    with open(d["file_path"], "w") as f:
        f.write("mock")

initial_state = {
    "applicant": {
        "first_name": "James",
        "last_name": "Smith",
        "email": "clear.approve@example.com",
        "phone": "9999988888",
        "dob": "1985-08-10",
        "monthly_income": 95000.0,
        "existing_emi": 8000.0,
        "loan_amount": 200000.0,
        "loan_purpose": "Home Improvement"
    },
    "documents": docs,
    "validation_result": None,
    "retrieved_policy": None,
    "score": None,
    "recommendation": None,
    "fairness_result": None,
    "audit_data": None,
    "human_approval": None,
    "metadata": {}
}

with patch.object(OCRProcessor, "is_tesseract_available", return_value=False):
    final_state = run_underwriting_workflow(initial_state)

print("RECOMMENDATION:", final_state.get("recommendation"))
print("VALIDATION RESULT:", final_state.get("validation_result"))
print("SCORE:", final_state.get("score"))
print("RETIREVED POLICY:", final_state.get("retrieved_policy"))

# Clean up
for d in docs:
    os.remove(d["file_path"])
os.rmdir(tmp_dir)
