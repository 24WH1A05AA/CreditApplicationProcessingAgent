import os
import re
import base64
import json
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from pypdf import PdfReader
from backend.utils.logging import logger
from backend.tools.ocr_processor import OCRProcessor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings

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
    forged: bool = False
    forgery_reason: Optional[str] = None

class AadhaarValidationResult(BaseModel):
    is_valid: bool
    aadhaar_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    error_message: Optional[str] = None
    forged: bool = False
    forgery_reason: Optional[str] = None

class SalarySlipValidationResult(BaseModel):
    is_valid: bool
    net_pay: Optional[float] = None
    employer_name: Optional[str] = None
    error_message: Optional[str] = None
    forged: bool = False
    forgery_reason: Optional[str] = None

class BankStatementValidationResult(BaseModel):
    is_valid: bool
    average_balance: Optional[float] = None
    total_deposits: Optional[float] = None
    error_message: Optional[str] = None
    forged: bool = False
    forgery_reason: Optional[str] = None

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
        metadata_warnings = []
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
            # Audit PDF metadata for tampering indicators
            pdf_meta = reader.metadata
            if pdf_meta:
                producer = str(pdf_meta.get("/Producer", "")).lower()
                creator = str(pdf_meta.get("/Creator", "")).lower()
                suspicious_tools = ["photoshop", "illustrator", "canva", "indesign", "coreldraw", "gimp", "pdfedit", "pdfill", "nitro", "sejda"]
                for tool in suspicious_tools:
                    if tool in producer or tool in creator:
                        metadata_warnings.append(f"PDF metadata indicates creation or modification using a graphic editor: {tool.capitalize()}")
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
            metadata={
                "file_name": os.path.basename(file_path),
                "page_count": page_count,
                "ocr_fallback": ocr_fallback_triggered,
                "file_path": file_path,
                "pdf_metadata_warnings": metadata_warnings
            }
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
                metadata={"file_name": os.path.basename(file_path), "parser": "pytesseract_ocr", "file_path": file_path}
            )
        except Exception as e:
            logger.error("Failed to run OCR on image %s: %s", file_path, str(e))
            raise ValueError(f"OCR parsing failed: {str(e)}")


class LLMDocumentValidator:
    """
    Leverages LLM capabilities to parse and validate documents, with regex/mock fallbacks.
    Supports both text-based parsing and multimodal (image-based) parsing when a multimodal model is configured.
    """
    @staticmethod
    def get_llm():
        is_mock_key = (
            not settings.OPENAI_API_KEY 
            or settings.OPENAI_API_KEY == "mock-key-for-development"
            or not settings.OPENAI_API_KEY.startswith("sk-")
        )
        if is_mock_key:
            return None
        try:
            return ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
                temperature=0.0,
                max_retries=2
            )
        except Exception as e:
            logger.error("Failed to initialize ChatOpenAI for validator: %s", str(e))
            return None

    @staticmethod
    def is_multimodal_supported() -> bool:
        # Check if the model name indicates multimodal support (like gpt-4o, gpt-4-vision, gemini)
        model = settings.OPENAI_MODEL.lower()
        return "gpt-4o" in model or "vision" in model or "gemini" in model or "claude-3" in model

    @staticmethod
    def parse_with_llm(parsed_doc: ParsedDocument, pydantic_model) -> Optional[BaseModel]:
        llm = LLMDocumentValidator.get_llm()
        if not llm:
            logger.info("Using regex/heuristic fallback (no valid API key configured).")
            return None
            
        doc_type = parsed_doc.document_type
        text = parsed_doc.extracted_text
        file_path = parsed_doc.metadata.get("file_path")
        metadata_warnings = parsed_doc.metadata.get("pdf_metadata_warnings", [])
        
        parser = JsonOutputParser(pydantic_object=pydantic_model)
        format_instructions = parser.get_format_instructions()
        
        warnings_context = ""
        if metadata_warnings:
            warnings_context = "PDF METADATA WARNINGS DETECTED ON THIS FILE:\n" + "\n".join([f"- {w}" for w in metadata_warnings]) + "\n\n"
            
        prompt_text = (
            f"You are a credit underwriting document verification and fraud prevention assistant.\n"
            f"Analyze the following document and extract the required fields for a {doc_type} document.\n"
            f"Ensure dates are formatted as DD/MM/YYYY or YYYY-MM-DD. If values are missing, output null.\n"
            f"Verify if the document is valid for the specified type (e.g. check if it is a {doc_type} document, contains the expected headers/fields, and is not a completely different document type).\n"
            f"If the document is invalid, not of the specified type, or has clear missing mandatory information, set `is_valid` to false and specify the reason in `error_message`.\n\n"
            f"FORGERY & TAMPER DETECTOR INSTRUCTIONS:\n"
            f"Analyze the document text and scan for inconsistencies or fraud indicators:\n"
            f"- For PAN/Aadhaar: check if formatting looks inconsistent, name spellings vary, or characters look edited.\n"
            f"- For Salary Slip: check if net pay makes mathematical sense (i.e., check if basic + allowances - deductions equals net pay), or if the employee name is mismatched.\n"
            f"- For Bank Statement: check if transaction columns, balances, or averages look modified or physically altered.\n"
            f"If there is any sign of digital tampering, numbers mismatch, or mathematical forgery, set `forged` to true and detail the reasons in `forgery_reason`. Otherwise set `forged` to false.\n\n"
            f"{warnings_context}"
            f"Extracted Text from OCR:\n\"\"\"\n{text}\n\"\"\"\n\n"
            f"{format_instructions}"
        )
        
        try:
            # Check if we can run multimodal analysis on images
            is_image = file_path and os.path.exists(file_path) and (file_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
            if is_image and LLMDocumentValidator.is_multimodal_supported():
                logger.info("Running multimodal LLM extraction for image %s...", os.path.basename(file_path))
                with open(file_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                
                content = [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
                message = HumanMessage(content=content)
                logger.info("Invoking multimodal LLM for %s...", doc_type)
                response = llm.invoke([message])
                result = parser.parse(response.content)
            else:
                logger.info("Running text-based LLM extraction for %s...", doc_type)
                messages = [
                    SystemMessage(content="You are an expert document parser and fraud auditor. Output only JSON."),
                    HumanMessage(content=prompt_text)
                ]
                response = llm.invoke(messages)
                result = parser.parse(response.content)
                
            result_obj = pydantic_model(**result)
            # Enforce metadata-based warnings
            if metadata_warnings:
                result_obj.forged = True
                reasons = [result_obj.forgery_reason] if result_obj.forgery_reason else []
                reasons.extend(metadata_warnings)
                result_obj.forgery_reason = "; ".join(reasons)
                
            return result_obj
        except Exception as e:
            logger.warning("LLM parsing failed for %s: %s. Falling back to regex parser.", doc_type, str(e))
            return None


class DocumentValidator:
    """
    Executes format validation and regex parsing for each supported document.
    """
    @staticmethod
    def validate_pan(parsed_doc: ParsedDocument) -> PANValidationResult:
        # LLM integration
        llm_res = LLMDocumentValidator.parse_with_llm(parsed_doc, PANValidationResult)
        if llm_res:
            logger.info("LLM successfully validated PAN.")
            return llm_res

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
        # LLM integration
        llm_res = LLMDocumentValidator.parse_with_llm(parsed_doc, AadhaarValidationResult)
        if llm_res:
            logger.info("LLM successfully validated Aadhaar.")
            return llm_res

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
        # LLM integration
        llm_res = LLMDocumentValidator.parse_with_llm(parsed_doc, SalarySlipValidationResult)
        if llm_res:
            logger.info("LLM successfully validated Salary Slip.")
            return llm_res

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
        # LLM integration
        llm_res = LLMDocumentValidator.parse_with_llm(parsed_doc, BankStatementValidationResult)
        if llm_res:
            logger.info("LLM successfully validated Bank Statement.")
            return llm_res

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
