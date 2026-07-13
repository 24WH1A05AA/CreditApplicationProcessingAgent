import pytest
from backend.tools.document_processor import (
    DocumentParser,
    DocumentValidator,
    ConsistencyChecker,
    ParsedDocument
)

def test_validate_pan_format():
    pan_text = """
    INCOME TAX DEPARTMENT
    GOVERNMENT OF INDIA
    NAME: JANE DOE
    DOB: 15/05/1990
    PAN: ABCDE1234F
    """
    parsed = ParsedDocument(document_type="PAN", extracted_text=pan_text)
    res = DocumentValidator.validate_pan(parsed)
    
    assert res.is_valid is True
    assert res.pan_number == "ABCDE1234F"
    assert res.name == "JANE DOE"
    assert res.dob == "15/05/1990"

def test_validate_aadhaar_format():
    aadhaar_text = """
    GOVERNMENT OF INDIA
    JANE DOE
    DOB: 15/05/1990
    GENDER: FEMALE
    Aadhaar Number: 1234 5678 9012
    """
    parsed = ParsedDocument(document_type="Aadhaar", extracted_text=aadhaar_text)
    res = DocumentValidator.validate_aadhaar(parsed)
    
    assert res.is_valid is True
    assert res.aadhaar_number == "123456789012"
    assert res.dob == "15/05/1990"

def test_validate_salary_slip():
    salary_text = """
    ACME CORP SERVICES PAYSLIP
    EMPLOYEE NAME: JANE DOE
    BASIC SALARY: 50,000
    NET PAY: 75,000 INR
    DEDUCTIONS: 5,000
    """
    parsed = ParsedDocument(document_type="Salary Slip", extracted_text=salary_text)
    res = DocumentValidator.validate_salary_slip(parsed)
    
    assert res.is_valid is True
    assert res.net_pay == 75000.0
    assert res.employer_name == "ACME CORP SERVICES PAYSLIP"

def test_validate_bank_statement():
    bank_text = """
    HDFC BANK STATEMENT
    ACCOUNT NO: 12345678
    AVERAGE BALANCE: 120,000 INR
    TOTAL DEPOSITS: 200,000
    """
    parsed = ParsedDocument(document_type="Bank Statement", extracted_text=bank_text)
    res = DocumentValidator.validate_bank_statement(parsed)
    
    assert res.is_valid is True
    assert res.average_balance == 120000.0
    assert res.total_deposits == 200000.0

def test_consistency_checks():
    # Setup data
    parsed_pan = ParsedDocument(
        document_type="PAN", 
        extracted_text="NAME: JANE DOE\nDOB: 15/05/1990\nPAN: ABCDE1234F"
    )
    parsed_aadhaar = ParsedDocument(
        document_type="Aadhaar", 
        extracted_text="JANE DOE\nDOB: 15/05/1990\n1234 5678 9012"
    )
    parsed_salary = ParsedDocument(
        document_type="Salary Slip", 
        extracted_text="ACME CORP PAYSLIP\nNET PAY: 75,000"
    )
    parsed_bank = ParsedDocument(
        document_type="Bank Statement", 
        extracted_text="BANK STATEMENT\nAVERAGE BALANCE: 50,000"
    )
    
    pan_res = DocumentValidator.validate_pan(parsed_pan)
    aadhaar_res = DocumentValidator.validate_aadhaar(parsed_aadhaar)
    salary_res = DocumentValidator.validate_salary_slip(parsed_salary)
    bank_res = DocumentValidator.validate_bank_statement(parsed_bank)
    
    app_data = {"first_name": "Jane", "last_name": "Doe", "dob": "1990-05-15", "monthly_income": 80000.0}

    # Match check
    res = ConsistencyChecker.check_identity_and_income_consistency(
        pan=pan_res, 
        aadhaar=aadhaar_res, 
        salary_slip=salary_res, 
        bank_statement=bank_res, 
        app_data=app_data
    )
    assert res.is_consistent is True
    assert len(res.discrepancies) == 0

    # Name mismatch check
    mismatch_pan_text = "NAME: JOHN SMITH\nDOB: 15/05/1990\nPAN: ABCDE1234F"
    mismatch_parsed_pan = ParsedDocument(document_type="PAN", extracted_text=mismatch_pan_text)
    mismatch_pan_res = DocumentValidator.validate_pan(mismatch_parsed_pan)
    
    res_mismatch = ConsistencyChecker.check_identity_and_income_consistency(
        pan=mismatch_pan_res, 
        aadhaar=aadhaar_res, 
        salary_slip=salary_res, 
        bank_statement=bank_res, 
        app_data=app_data
    )
    assert res_mismatch.is_consistent is False
    assert any("PAN card" in d for d in res_mismatch.discrepancies)
