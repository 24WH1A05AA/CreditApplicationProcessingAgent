from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.rag.pipeline import rag_pipeline
from backend.utils.logging import logger

# ================= Structured Pydantic Output Models =================

class PolicyMatch(BaseModel):
    parameter: str = Field(..., description="DTI, Credit Score, Income, or Defaults")
    value: str = Field(..., description="Stated actual value of the applicant")
    clause_cited: str = Field(..., description="Matched policy clause code (e.g., CP-DTI-01)")
    policy_text: str = Field(..., description="Verbatim text of the policy clause")
    status: str = Field(..., description="PASSED, REFER, FAILED")
    reasoning: str = Field(..., description="Underwriter reasoning for matching clause decision")

class PolicyEvaluationSummary(BaseModel):
    matches: List[PolicyMatch] = Field(default_factory=list)
    all_passed: bool
    any_failed: bool
    any_refer: bool


# ================= Core Implementations =================

class CreditPolicyEngine:
    @staticmethod
    def evaluate_policy(
        credit_score: int,
        dti_ratio: float,
        monthly_income: float,
        has_active_defaults: bool
    ) -> PolicyEvaluationSummary:
        """
        Evaluates applicant's financial attributes against credit policies retrieved using RAG.
        """
        logger.info("Evaluating credit policy against retrieved RAG clauses...")
        matches = []
        
        # 1. DTI Policy Evaluation
        dti_results = rag_pipeline.retrieve("What is the maximum allowed DTI ratio?", k=10)
        dti_clause = next((r for r in dti_results if r["citation"] == "CP-DTI-01"), None)
        if not dti_clause and dti_results:
            dti_clause = dti_results[0]
            
        if dti_clause:
            if dti_ratio <= 0.40:
                dti_status = "PASSED"
                dti_reason = f"Applicant's DTI of {dti_ratio:.2%} is within the standard limit (<= 40%) specified in CP-DTI-01."
            elif dti_ratio <= 0.45:
                dti_status = "REFER"
                dti_reason = f"Applicant's DTI of {dti_ratio:.2%} falls into the borderline range (40% - 45%) which requires manual underwriter review per CP-DTI-01."
            else:
                dti_status = "FAILED"
                dti_reason = f"Applicant's DTI of {dti_ratio:.2%} exceeds the maximum allowable threshold of 45% specified in CP-DTI-01."
                
            matches.append(PolicyMatch(
                parameter="DTI",
                value=f"{dti_ratio:.2%}",
                clause_cited=dti_clause["citation"],
                policy_text=dti_clause["content"],
                status=dti_status,
                reasoning=dti_reason
            ))

        # 2. Credit Score Policy Evaluation
        cs_results = rag_pipeline.retrieve("Underwrite applicant based on credit score", k=10)
        cs_clause = next((r for r in cs_results if r["citation"] == "CP-CS-01"), None)
        if not cs_clause and cs_results:
            cs_clause = cs_results[0]
            
        if cs_clause:
            if credit_score >= 750:
                cs_status = "PASSED"
                cs_reason = f"Credit score of {credit_score} is excellent (>= 750) qualifying for standard approval per CP-CS-01."
            elif credit_score >= 650:
                cs_status = "REFER"
                cs_reason = f"Credit score of {credit_score} is standard (650-749), requiring manual underwriting referral per CP-CS-01."
            else:
                cs_status = "FAILED"
                cs_reason = f"Credit score of {credit_score} is below the minimum threshold (< 650) for automatic rejection per CP-CS-01."
                
            matches.append(PolicyMatch(
                parameter="Credit Score",
                value=str(credit_score),
                clause_cited=cs_clause["citation"],
                policy_text=cs_clause["content"],
                status=cs_status,
                reasoning=cs_reason
            ))

        # 3. Monthly Income Policy Evaluation
        inc_results = rag_pipeline.retrieve("What is the minimum monthly income?", k=10)
        inc_clause = next((r for r in inc_results if r["citation"] == "CP-INC-01"), None)
        if not inc_clause and inc_results:
            inc_clause = inc_results[0]
            
        if inc_clause:
            min_required = 25000.0  # Salaried base limit
            if monthly_income >= min_required:
                inc_status = "PASSED"
                inc_reason = f"Stated income of INR {monthly_income:,.2f} meets the minimum requirement of INR {min_required:,.2f} per CP-INC-01."
            else:
                inc_status = "FAILED"
                inc_reason = f"Stated income of INR {monthly_income:,.2f} is below the minimum required INR {min_required:,.2f} per CP-INC-01."
                
            matches.append(PolicyMatch(
                parameter="Monthly Income",
                value=f"INR {monthly_income:,.2f}",
                clause_cited=inc_clause["citation"],
                policy_text=inc_clause["content"],
                status=inc_status,
                reasoning=inc_reason
            ))

        # 4. Defaults Policy Evaluation
        def_results = rag_pipeline.retrieve("Check defaults write-offs history", k=10)
        def_clause = next((r for r in def_results if r["citation"] == "CP-CS-02"), None)
        if not def_clause and def_results:
            def_clause = def_results[0]
            
        if def_clause:
            if not has_active_defaults:
                def_status = "PASSED"
                def_reason = "Applicant has no active default history in the last 12 months, satisfying CP-CS-02."
            else:
                def_status = "FAILED"
                def_reason = "Applicant reports active defaults/write-offs within the last 12 months, triggering automatic decline per CP-CS-02."
                
            matches.append(PolicyMatch(
                parameter="Active Defaults",
                value="Yes" if has_active_defaults else "No",
                clause_cited=def_clause["citation"],
                policy_text=def_clause["content"],
                status=def_status,
                reasoning=def_reason
            ))

        # Determine overall indicators
        all_passed = all(m.status == "PASSED" for m in matches)
        any_failed = any(m.status == "FAILED" for m in matches)
        any_refer = any(m.status == "REFER" for m in matches)

        return PolicyEvaluationSummary(
            matches=matches,
            all_passed=all_passed,
            any_failed=any_failed,
            any_refer=any_refer
        )
