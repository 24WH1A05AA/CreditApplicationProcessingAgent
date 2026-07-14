import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text
)
from sqlalchemy.orm import relationship
from backend.database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(String, primary_key=True, default=generate_uuid)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dob = Column(String, nullable=False)  # ISO Date String (YYYY-MM-DD)
    email = Column(String, unique=True, index=True, nullable=False)
    monthly_income = Column(Float, nullable=False)
    existing_emi = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    applicant_id = Column(String, ForeignKey("applicants.id"), nullable=False)
    loan_amount = Column(Float, nullable=False)
    loan_purpose = Column(String, nullable=False)
    status = Column(String, default="INTAKE")  # INTAKE, DOC_VALIDATION, EVALUATION, PENDING_APPROVAL, APPROVED, DECLINED, REFER
    credit_score = Column(Integer, nullable=True)
    dti_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applicant = relationship("Applicant", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    policy_results = relationship("PolicyResult", back_populates="application", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="application", cascade="all, delete-orphan")
    human_decisions = relationship("HumanDecision", back_populates="application", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="application", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    document_type = Column(String, nullable=False)  # PAN, Aadhaar, Salary Slip, Bank Statement
    file_path = Column(String, nullable=False)
    is_valid = Column(Boolean, nullable=True)
    validation_result = Column(JSON, nullable=True)  # Detailed validation response
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="documents")


class PolicyResult(Base):
    __tablename__ = "policy_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    policy_name = Column(String, nullable=False)  # e.g., DTI, Credit Score, KYC
    status = Column(String, nullable=False)  # PASSED, FAILED, REFER
    details = Column(Text, nullable=True)
    rule_cited = Column(Text, nullable=True)  # Clause citations from policy docs
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="policy_results")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    decision = Column(String, nullable=False)  # APPROVE, REFER, DECLINE
    reasoning = Column(Text, nullable=False)
    composite_score = Column(Float, nullable=False)
    fairness_passed = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="recommendations")


class HumanDecision(Base):
    __tablename__ = "human_decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    decision = Column(String, nullable=False)  # APPROVED, DECLINED, REFER
    comments = Column(Text, nullable=True)
    underwriter_email = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="human_decisions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    action = Column(String, nullable=False)  # e.g., INTAKE, VALIDATE_DOCS, RUN_POLICY, RECOMMENDATION, HUMAN_APPROVAL
    performed_by = Column(String, nullable=False)  # e.g. system, underwriter_email
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="audit_logs")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # ADMIN, UNDERWRITER, AUDITOR
    created_at = Column(DateTime, default=datetime.utcnow)
