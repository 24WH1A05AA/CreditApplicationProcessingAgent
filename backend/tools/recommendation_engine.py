from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.utils.logging import logger

# ================= Structured Pydantic Output Models =================

class RecommendationOutput(BaseModel):
    decision: str = Field(..., description="APPROVE, REFER, DECLINE")
    reasons: List[str] = Field(default_factory=list, description="Reasons justifying the underwriting decision")
    policy_citations: List[str] = Field(default_factory=list, description="Citations of matching policy clauses")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0) based on credit profile strength")


# ================= Core Implementations =================

class RecommendationEngine:
    @staticmethod
    def generate_recommendation(
        validation_result: Dict[str, Any],
        score_result: Dict[str, Any],
        retrieved_policy: Dict[str, Any]
    ) -> RecommendationOutput:
        """
        Synthesizes validation results, credit scores, and RAG policy decisions 
        to produce a structured recommendation with citations and confidence metrics.
        """
        logger.info("Generating lending recommendation...")
        
        decision = "APPROVE"
        reasons = []
        citations = []
        
        # 1. Evaluate Document Completeness & Consistency
        is_complete = validation_result.get("is_complete", True)
        missing_docs = validation_result.get("missing_documents", [])
        consistency = validation_result.get("consistency", {})
        is_consistent = consistency.get("is_consistent", True)
        discrepancies = consistency.get("discrepancies", [])
        
        if not is_complete:
            decision = "DECLINE"
            reasons.append(f"Incomplete documentation. Missing: {', '.join(missing_docs)}")
            citations.append("FP-DOC-01")
            
        if not is_consistent:
            # If documents are inconsistent, recommend REFER for manual review
            if decision != "DECLINE":
                decision = "REFER"
            reasons.append(f"Document discrepancies detected: {', '.join(discrepancies)}")
            citations.append("FP-DOC-02")

        # 2. Evaluate Credit Bureau & Debt checks
        credit_score = score_result.get("credit_score", 700)
        has_defaults = score_result.get("has_active_defaults", False)
        dti_ratio = score_result.get("dti_ratio", 0.0)
        dti_status = score_result.get("dti_status", "PASSED")
        
        if has_defaults:
            decision = "DECLINE"
            reasons.append("Active defaults or write-offs reported in the last 12 months.")
            citations.append("CP-CS-02")
            
        if credit_score < 650:
            decision = "DECLINE"
            reasons.append(f"Bureau credit score of {credit_score} is below minimum approval threshold of 650.")
            citations.append("CP-CS-01")
        elif credit_score < 750:
            if decision != "DECLINE":
                decision = "REFER"
            reasons.append(f"Credit score of {credit_score} is in the referral range (650-749).")
            citations.append("CP-CS-01")
            
        if dti_ratio > 0.45:
            decision = "DECLINE"
            reasons.append(f"Debt-to-Income (DTI) ratio of {dti_ratio:.2%} exceeds maximum allowed 45%.")
            citations.append("CP-DTI-01")
        elif dti_ratio > 0.40:
            if decision != "DECLINE":
                decision = "REFER"
            reasons.append(f"DTI ratio of {dti_ratio:.2%} is in borderline range (40%-45%).")
            citations.append("CP-DTI-01")

        # 3. Incorporate RAG-based Credit Policy overrides
        matches = retrieved_policy.get("matches", [])
        any_failed = retrieved_policy.get("any_failed", False)
        any_refer = retrieved_policy.get("any_refer", False)
        
        for m in matches:
            citation_code = m.get("clause_cited")
            status = m.get("status")
            reasoning = m.get("reasoning")
            
            if status == "FAILED":
                decision = "DECLINE"
                reasons.append(f"Policy check failed for {m.get('parameter')}: {reasoning}")
                if citation_code not in citations:
                    citations.append(citation_code)
            elif status == "REFER":
                if decision != "DECLINE":
                    decision = "REFER"
                reasons.append(f"Policy check referred for {m.get('parameter')}: {reasoning}")
                if citation_code not in citations:
                    citations.append(citation_code)
            else:
                # Keep passed citations to justify decisions
                if citation_code not in citations:
                    citations.append(citation_code)

        # 4. Calculate Underwriting Confidence Score
        # Confidence is higher for clear-cut approves/declines and lower for borderline referrals.
        if decision == "APPROVE":
            # Highly qualified candidates have credit score >= 780 and DTI <= 0.35
            if credit_score >= 780 and dti_ratio <= 0.35:
                confidence = 0.95
            else:
                confidence = 0.88
        elif decision == "DECLINE":
            # Clear decline indicators (active defaults, low score, high DTI)
            if has_defaults or credit_score < 600 or dti_ratio > 0.50:
                confidence = 0.98
            else:
                confidence = 0.90
        else:
            # REFER requires manual intervention, hence lower recommendation confidence
            confidence = 0.75

        # Clean up citations: Ensure general fallback citation if empty
        if not citations:
            citations.append("General Underwriting Policy")

        # Fallback reasoning if everything passed perfectly
        if not reasons:
            reasons.append("All underwriting checks, document validations, and RAG policies successfully satisfied.")

        return RecommendationOutput(
            decision=decision,
            reasons=reasons,
            policy_citations=citations,
            confidence=confidence
        )
