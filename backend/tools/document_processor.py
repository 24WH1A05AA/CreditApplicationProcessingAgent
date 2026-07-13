import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from pypdf import PdfReader
from backend.utils.logging import logger
from backend.tools.ocr_processor import OCRProcessor

# ================= Structured Pydantic Output Models =================

class ParsedDocument(BaseModel):
    document_type: str = Field(..., description="PAN, Aadhaar, Salary Slip, Bank Statement")
    extracted_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PANValidationResult(BaseModel):
    is_valid: bool
    pan_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    error_message: Optional[str] = None

class AadhaarValidationResult(BaseModel):
    is_valid: bool
    aadhaar_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    error_message: Optional[str] = None

class SalarySlipValidationResult(BaseModel):
    is_valid: bool
    net_pay: Optional[float] = None
    employer_name: Optional[str] = None
    error_message: Optional[str] = None

class BankStatementValidationResult(BaseModel):
    is_valid: bool
    average_balance: Optional[float] = None
    total_deposits: Optional[float] = None
    error_message: Optional[str] = None

class ValidationSummary(BaseModel):
    is_complete: bool
    pan: Optional[PANValidationResult] = None
    aadhaar: Optional[AadhaarValidationResult] = None
    salary_slip: Optional[SalarySlipValidationResult] = None
    bank_statement: Optional[BankStatementValidationResult] = None
    missing_documents: List[str] = Field(default_factory=list)

class ConsistencyResult(BaseModel):
    is_consistent: bool
    discrepancies: List[str] = Field(default_factory=list)


# ================= Helper Utilities =================

def normalize_date(date_str: Optional[str]) -> str:
    """
    Standardizes date strings (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY) to YYYY-MM-DD.
    """
    if not date_str:
        return ""
    date_str = date_str.strip()
    
    # Check YYYY-MM-DD or YYYY/MM/DD
    match_yyyy = re.match(r"^(\d{4})[/\-](\d{2})[/\-](\d{2})$", date_str)
    if match_yyyy:
        return f"{match_yyyy.group(1)}-{match_yyyy.group(2)}-{match_yyyy.group(3)}"
        
    # Check DD/MM/YYYY or DD-MM-YYYY
    match_dd = re.match(r"^(\d{2})[/\-](\d{2})[/\-](\d{4})$", date_str)
    if match_dd:
        return f"{match_dd.group(3)}-{match_dd.group(2)}-{match_dd.group(1)}"
        
    return date_str


# ================= Core Implementations =================

class DocumentParser:
    """
    Handles file type detection and text extraction from PDFs and Images.
    """
    @staticmethod
    def parse_pdf(file_path: str, document_type: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        text = ""
        page_count = 0
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as pdf_err:
            logger.warning("Failed standard PDF extraction on %s: %s. Attempting OCR...", file_path, str(pdf_err))
            
        # If PDF text is empty/short or standard extraction failed, trigger OCR fallback
        ocr_fallback_triggered = False
        if len(text.strip()) < 10:
            logger.info("PDF content is empty or scanned image. Triggering scanned PDF OCR fallback...")
            try:
                text = OCRProcessor.extract_text_from_pdf_pages(file_path)
                ocr_fallback_triggered = True
            except Exception as ocr_err:
                logger.error("OCR fallback failed on %s: %s", file_path, str(ocr_err))
                raise ValueError(f"Failed to extract text from PDF: standard parser and OCR both failed.")
                
        return ParsedDocument(
            document_type=document_type,
            extracted_text=text,
            metadata={"file_name": os.path.basename(file_path), "page_count": page_count, "ocr_fallback": ocr_fallback_triggered}
        )

    @staticmethod
    def parse_image(file_path: str, document_type: str) -> ParsedDocument:
        """
        Parses JPEG/PNG images using OCRProcessor.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            text = OCRProcessor.extract_text_from_image(file_path)
            return ParsedDocument(
                document_type=document_type,
                extracted_text=text,
                metadata={"file_name": os.path.basename(file_path), "parser": "pytesseract_ocr"}
            )
        except Exception as e:
            logger.error("Failed to run OCR on image %s: %s", file_path, str(e))
            raise ValueError(f"OCR parsing failed: {str(e)}")


class DocumentValidator:
    """
    Executes format validation and regex parsing for each supported document.
    """
    @staticmethod
    def validate_pan(parsed_doc: ParsedDocument) -> PANValidationResult:
        text = parsed_doc.extracted_text.upper()
        # Regex for standard Indian PAN: 5 letters, 4 digits, 1 letter
        pan_regex = r"[A-Z]{5}[0-9]{4}[A-Z]{1}"
        match = re.search(pan_regex, text)
        
        if not match:
            return PANValidationResult(is_valid=False, error_message="Invalid PAN format or PAN not found")
            
        pan_number = match.group(0)
        name = None
        dob = None
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for i, line in enumerate(lines):
            # Extract name near name headers
            if "NAME" in line:
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1 and parts[1].strip():
                        name = parts[1].strip()
                        continue
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if not any(k in next_line for k in ["FATHER", "INDIA", "INCOME"]):
                        name = next_line
            # DOB match: DD/MM/YYYY or DD-MM-YYYY
            dob_match = re.search(r"(\d{2}[/\-]\d{2}[/\-]\d{4})", line)
            if dob_match:
                dob = dob_match.group(1)
                
        return PANValidationResult(
            is_valid=True,
            pan_number=pan_number,
            name=name.strip() if name else None,
            dob=dob.strip() if dob else None
        )

    @staticmethod
    def validate_aadhaar(parsed_doc: ParsedDocument) -> AadhaarValidationResult:
        text = parsed_doc.extracted_text
        # Regex for standard 12 digit Aadhaar (with/without space separators)
        aadhaar_regex = r"\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b"
        match = re.search(aadhaar_regex, text)
        
        if not match:
            return AadhaarValidationResult(is_valid=False, error_message="Invalid Aadhaar format or Aadhaar number not found")
            
        aadhaar_number = match.group(0).replace(" ", "")
        name = None
        dob = None
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for line in lines:
            if "NAME" in line.upper() and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    name = parts[1].strip()
            # Match DOB or Year of birth
            dob_match = re.search(r"(?:DOB|Birth|Year of Birth)[:\s]*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4})", line, re.IGNORECASE)
            if dob_match:
                dob = dob_match.group(1)
                
        # Find name on early lines if not found
        if not name:
            for line in lines[:5]:
                if not any(k in line.upper() for k in ["GOVERNMENT", "UNIQUE", "IDENTIFICATION", "AADHAAR", "DOB", "MALE", "FEMALE"]):
                    name = line
                    break
                
        return AadhaarValidationResult(
            is_valid=True,
            aadhaar_number=aadhaar_number,
            name=name.strip() if name else None,
            dob=dob.strip() if dob else None
        )

    @staticmethod
    def validate_salary_slip(parsed_doc: ParsedDocument) -> SalarySlipValidationResult:
        text = parsed_doc.extracted_text
        lines = text.split("\n")
        
        salary_keywords = ["SALARY", "PAYSLIP", "PAY SLIP", "EARNINGS", "BASIC", "GROSS", "NET PAY"]
        has_keywords = any(any(kw in line.upper() for kw in salary_keywords) for line in lines)
        
        if not has_keywords:
            return SalarySlipValidationResult(is_valid=False, error_message="Missing salary slip indicators/headers")
            
        net_pay = None
        employer_name = None
        
        # Net Pay Extraction
        net_pay_match = re.search(r"(?:NET PAY|NET SALARY|TAKE HOME|TOTAL EARNINGS)[:\s]*[INR\s]*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if net_pay_match:
            try:
                net_pay = float(net_pay_match.group(1).replace(",", ""))
            except ValueError:
                pass
                
        # Employer Name Heuristic (usually first line with corporate indicator)
        for line in lines[:3]:
            if any(k in line.upper() for k in ["LTD", "LIMITED", "INC", "CORP", "SERVICES", "TECHNOLOGIES"]):
                employer_name = line.strip()
                break
                
        return SalarySlipValidationResult(
            is_valid=True,
            net_pay=net_pay,
            employer_name=employer_name
        )

    @staticmethod
    def validate_bank_statement(parsed_doc: ParsedDocument) -> BankStatementValidationResult:
        text = parsed_doc.extracted_text
        lines = text.split("\n")
        
        statement_keywords = ["STATEMENT", "TRANSACTION", "BALANCE", "ACCOUNT NO", "WITHDRAWAL", "DEPOSIT"]
        has_keywords = any(any(kw in line.upper() for kw in statement_keywords) for line in lines)
        
        if not has_keywords:
            return BankStatementValidationResult(is_valid=False, error_message="Missing bank statement indicators/headers")
            
        # Try extracting average balance or total deposits
        avg_bal = None
        tot_dep = None
        
        # Search for Average Balance (heuristics)
        avg_bal_match = re.search(r"(?:AVERAGE BALANCE|AVG BAL|CLOSING BALANCE)[:\s]*[INR\s]*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if avg_bal_match:
            try:
                avg_bal = float(avg_bal_match.group(1).replace(",", ""))
            except ValueError:
                pass
                
        # Search for Total Deposits (heuristics)
        tot_dep_match = re.search(r"(?:TOTAL DEPOSITS|TOTAL CREDITS)[:\s]*[INR\s]*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if tot_dep_match:
            try:
                tot_dep = float(tot_dep_match.group(1).replace(",", ""))
            except ValueError:
                pass
                
        return BankStatementValidationResult(
            is_valid=True,
            average_balance=avg_bal,
            total_deposits=tot_dep
        )


class ConsistencyChecker:
    """
    Compares document fields with application details to identify discrepancies.
    """
    @staticmethod
    def check_identity_and_income_consistency(
        pan: Optional[PANValidationResult],
        aadhaar: Optional[AadhaarValidationResult],
        salary_slip: Optional[SalarySlipValidationResult],
        bank_statement: Optional[BankStatementValidationResult],
        app_data: Dict[str, Any]
    ) -> ConsistencyResult:
        discrepancies = []
        
        app_name = f"{app_data.get('first_name', '')} {app_data.get('last_name', '')}".strip().lower()
        app_dob = normalize_date(app_data.get("dob", ""))
        
        # 1. Check PAN Consistency
        if pan and pan.is_valid:
            if pan.name:
                pan_name_lower = pan.name.lower()
                if not (pan_name_lower in app_name or app_name in pan_name_lower):
                    discrepancies.append(f"Name mismatch on PAN card: '{pan.name}' vs Application: '{app_data.get('first_name')} {app_data.get('last_name')}'")
            if pan.dob and app_dob:
                pan_dob_normalized = normalize_date(pan.dob)
                if pan_dob_normalized != app_dob:
                    discrepancies.append(f"DOB mismatch on PAN card: '{pan.dob}' vs Application: '{app_data.get('dob')}'")
                    
        # 2. Check Aadhaar Consistency
        if aadhaar and aadhaar.is_valid:
            if aadhaar.name:
                aadhaar_name_lower = aadhaar.name.lower()
                if not (aadhaar_name_lower in app_name or app_name in aadhaar_name_lower):
                    discrepancies.append(f"Name mismatch on Aadhaar card: '{aadhaar.name}' vs Application: '{app_data.get('first_name')} {app_data.get('last_name')}'")
            if aadhaar.dob and app_dob:
                aadhaar_dob_normalized = normalize_date(aadhaar.dob)
                if len(aadhaar_dob_normalized) == 4:  # Only Birth Year on Aadhaar
                    if aadhaar_dob_normalized not in app_dob:
                        discrepancies.append(f"Birth year mismatch on Aadhaar card: '{aadhaar.dob}' vs Application: '{app_data.get('dob')}'")
                elif aadhaar_dob_normalized != app_dob:
                    discrepancies.append(f"DOB mismatch on Aadhaar card: '{aadhaar.dob}' vs Application: '{app_data.get('dob')}'")

        # 3. Income check
        if salary_slip and salary_slip.is_valid and salary_slip.net_pay:
            app_income = float(app_data.get("monthly_income", 0.0))
            # Flag a discrepancy if slip salary is less than 85% of stated income
            if salary_slip.net_pay < (app_income * 0.85):
                discrepancies.append(f"Stated monthly income (INR {app_income}) is significantly higher than salary slip net pay (INR {salary_slip.net_pay})")

        return ConsistencyResult(
            is_consistent=len(discrepancies) == 0,
            discrepancies=discrepancies
        )
