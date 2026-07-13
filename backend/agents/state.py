from typing import TypedDict, List, Dict, Any, Optional
from backend.models.schemas import (
    ApplicantCreate,
    RecommendationBase,
    HumanDecisionCreate,
    AuditLogBase
)
from backend.tools.document_processor import ValidationSummary, ConsistencyResult
from backend.tools.policy_engine import PolicyEvaluationSummary
from backend.tools.credit_engine import RiskScoreResult

class UnderwritingState(TypedDict):
    """
    Shared state configuration for the LangGraph Loan Underwriting Workflow.
    Designed to be highly modular, strongly typed, and easily extensible.
    """
    # 1. Stated Applicant Info
    applicant: Dict[str, Any]
    
    # 2. Uploaded Document Paths/metadata
    documents: List[Dict[str, Any]]
    
    # 3. Document Validation & Verification checks
    validation_result: Optional[Dict[str, Any]]
    
    # 4. RAG-matched policy clauses and citations
    retrieved_policy: Optional[Dict[str, Any]]
    
    # 5. DTI, Bureau Score, and Composite Risk Score results
    score: Optional[Dict[str, Any]]
    
    # 6. AI Recommendation (APPROVE, REFER, DECLINE) and citations
    recommendation: Optional[Dict[str, Any]]
    
    # 7. Fairness validations (demographic-blind re-score check)
    fairness_result: Optional[Dict[str, Any]]
    
    # 8. Complete Audit trail metadata
    audit_data: Optional[Dict[str, Any]]
    
    # 9. Human underwriter final decision signature
    human_approval: Optional[Dict[str, Any]]
    
    # 10. Extensible metadata container for future custom attributes/tracing
    metadata: Dict[str, Any]
