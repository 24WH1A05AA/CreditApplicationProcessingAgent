import os
import json
from PIL import Image

def generate_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    apps_dir = os.path.join(base_dir, "applications")
    docs_dir = os.path.join(base_dir, "documents")
    
    os.makedirs(apps_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    # 1. Generate Applications JSONs
    applications = {
        "approve_jane_doe.json": {
            "loan_amount": 150000.0,
            "loan_purpose": "Home Improvement",
            "applicant": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "clear.approve@example.com",
                "phone": "9999988888",
                "dob": "1990-05-15",
                "monthly_income": 75000.0,
                "existing_emi": 5000.0
            }
        },
        "refer_nancy_wheeler.json": {
            "loan_amount": 350000.0,
            "loan_purpose": "Personal Loan",
            "applicant": {
                "first_name": "Nancy",
                "last_name": "Wheeler",
                "email": "borderline.refer@example.com",
                "phone": "9999911111",
                "dob": "1994-03-12",
                "monthly_income": 50000.0,
                "existing_emi": 0.0
            }
        },
        "decline_missing_docs_robert.json": {
            "loan_amount": 100000.0,
            "loan_purpose": "Debt Consolidation",
            "applicant": {
                "first_name": "Robert",
                "last_name": "Baratheon",
                "email": "clear.approve@example.com",
                "phone": "9999922222",
                "dob": "1975-01-01",
                "monthly_income": 120000.0,
                "existing_emi": 5000.0
            }
        },
        "decline_low_score_loki.json": {
            "loan_amount": 100000.0,
            "loan_purpose": "Car Loan",
            "applicant": {
                "first_name": "Loki",
                "last_name": "Laufeyson",
                "email": "declined.lowscore@example.com",
                "phone": "9999944444",
                "dob": "1992-06-06",
                "monthly_income": 40000.0,
                "existing_emi": 1000.0
            }
        },
        "decline_defaults_joffrey.json": {
            "loan_amount": 120000.0,
            "loan_purpose": "Debt Consolidation",
            "applicant": {
                "first_name": "Joffrey",
                "last_name": "Baratheon",
                "email": "default@example.com",
                "phone": "9999955555",
                "dob": "1995-10-10",
                "monthly_income": 80000.0,
                "existing_emi": 2000.0
            }
        }
    }
    
    for filename, data in applications.items():
        file_path = os.path.join(apps_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Generated application: {file_path}")
        
    # 2. Generate Mock Document files
    # Helper to generate a small white image
    def create_dummy_image(name):
        path = os.path.join(docs_dir, name)
        img = Image.new("RGB", (200, 200), color="white")
        img.save(path)
        print(f"Generated image document: {path}")
        
    # Helper to generate a dummy scanned pdf
    def create_dummy_pdf(name):
        path = os.path.join(docs_dir, name)
        with open(path, "w") as f:
            f.write("")
        print(f"Generated PDF document: {path}")

    # Generate documents with filenames matching mock OCR requirements
    create_dummy_image("jane_doe_pan.png")
    create_dummy_image("jane_doe_aadhaar.png")
    create_dummy_pdf("jane_doe_salary_slip.pdf")
    create_dummy_pdf("jane_doe_bank_statement.pdf")
    
    create_dummy_image("nancy_wheeler_pan.png")
    create_dummy_image("nancy_wheeler_aadhaar.png")
    create_dummy_pdf("nancy_wheeler_salary_slip.pdf")
    create_dummy_pdf("nancy_wheeler_bank_statement.pdf")

    create_dummy_image("robert_baratheon_pan.png")
    create_dummy_image("robert_baratheon_aadhaar.png")

    create_dummy_image("loki_laufeyson_pan.png")
    create_dummy_image("loki_laufeyson_aadhaar.png")
    create_dummy_pdf("loki_laufeyson_salary_slip.pdf")
    create_dummy_pdf("loki_laufeyson_bank_statement.pdf")

    create_dummy_image("joffrey_baratheon_pan.png")
    create_dummy_image("joffrey_baratheon_aadhaar.png")
    create_dummy_pdf("joffrey_baratheon_salary_slip.pdf")
    create_dummy_pdf("joffrey_baratheon_bank_statement.pdf")
    
    # 3. Generate plain text reference files so users can see what content gets extracted
    text_docs = {
        "jane_doe_pan_text.txt": """INCOME TAX DEPARTMENT
GOVERNMENT OF INDIA
NAME: JANE DOE
DOB: 15/05/1990
PAN: ABCDE1234F""",
        "jane_doe_aadhaar_text.txt": """GOVERNMENT OF INDIA
JANE DOE
DOB: 15/05/1990
GENDER: FEMALE
Aadhaar Number: 1234 5678 9012""",
        "jane_doe_salary_slip_text.txt": """ACME CORP SERVICES PAYSLIP
EMPLOYEE NAME: JANE DOE
BASIC SALARY: 50,000
NET PAY: 75,000 INR
DEDUCTIONS: 5,000""",
        "jane_doe_bank_statement_text.txt": """HDFC BANK STATEMENT
ACCOUNT NO: 12345678
AVERAGE BALANCE: 120,000 INR
TOTAL DEPOSITS: 200,000"""
    }
    
    for filename, content in text_docs.items():
        file_path = os.path.join(docs_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated text reference document: {file_path}")

if __name__ == "__main__":
    generate_data()
