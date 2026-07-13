from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ================= Applicant Schemas =================
class ApplicantBase(BaseModel):
    first_name: str
    last_name: str
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    email: EmailStr
    monthly_income: float = Field(..., gt=0, description="Monthly income in INR")
    existing_emi: float = Field(default=0.0, ge=0, description="Total existing EMIs in INR")

class ApplicantCreate(ApplicantBase):
    pass

class Applicant(ApplicantBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================= Document Schemas =================
class DocumentBase(BaseModel):
    document_type: str = Field(..., description="PAN, Aadhaar, Salary Slip, Bank Statement")
    file_path: str

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: str
    application_id: str
    is_valid: Optional[bool] = None
    validation_result: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ================= PolicyResult Schemas =================
class PolicyResultBase(BaseModel):
    policy_name: str
    status: str  # PASSED, FAILED, REFER
    details: Optional[str] = None
    rule_cited: Optional[str] = None

class PolicyResult(PolicyResultBase):
    id: str
    application_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================= Recommendation Schemas =================
class RecommendationBase(BaseModel):
    decision: str  # APPROVE, REFER, DECLINE
    reasoning: str
    composite_score: float
    fairness_passed: Optional[bool] = None

class Recommendation(RecommendationBase):
    id: str
    application_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================= HumanDecision Schemas =================
class HumanDecisionBase(BaseModel):
    decision: str  # APPROVED, DECLINED, REFER
    comments: Optional[str] = None
    underwriter_email: EmailStr

class HumanDecisionCreate(HumanDecisionBase):
    application_id: str

class HumanDecision(HumanDecisionBase):
    id: str
    application_id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ================= AuditLog Schemas =================
class AuditLogBase(BaseModel):
    action: str
    performed_by: str
    details: Optional[Dict[str, Any]] = None

class AuditLog(AuditLogBase):
    id: str
    application_id: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ================= Application Schemas =================
class ApplicationBase(BaseModel):
    loan_amount: float = Field(..., gt=0, description="Requested loan amount in INR")
    loan_purpose: str

class ApplicationCreate(ApplicationBase):
    applicant: ApplicantCreate

class Application(ApplicationBase):
    id: str
    applicant_id: str
    status: str
    credit_score: Optional[int] = None
    dti_ratio: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    # Nested relationships if needed
    applicant: Optional[Applicant] = None
    documents: List[Document] = []
    policy_results: List[PolicyResult] = []
    recommendations: List[Recommendation] = []
    human_decisions: List[HumanDecision] = []

    class Config:
        from_attributes = True
