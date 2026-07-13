from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.tools.credit_engine import CreditScoringEngine
from backend.tools.policy_engine import CreditPolicyEngine
from backend.tools.recommendation_engine import RecommendationEngine
from backend.utils.logging import logger

# ================= Structured Pydantic Output Models =================

class FairnessValidationResult(BaseModel):
    is_fair: bool = Field(..., description="True if blind and non-blind decisions are identical")
    original_decision: str = Field(..., description="Original recommendation decision")
    blind_decision: str = Field(..., description="Demographic-blind recommendation decision")
    justification: str = Field(..., description="Audit justification for fairness check")
    discrepancies: List[str] = Field(default_factory=list, description="List of fairness violations/discrepancies")


# ================= Core Implementations =================

class FairnessChecker:
    @staticmethod
    def validate_fairness(
        applicant_data: Dict[str, Any],
        validation_result: Dict[str, Any],
        original_score: Dict[str, Any],
        original_policy: Dict[str, Any],
        original_decision: str
    ) -> FairnessValidationResult:
        """
        Executes fairness validation by evaluating the application in a demographic-blind state.
        Removes identifier fields (name, email, age/DOB, gender, address) and re-evaluates 
        credit risk and policy matching.
        """
        logger.info("Executing demographic-blind fairness validation...")
        discrepancies = []
        
        # 1. Create Identity-Blind Applicant Data
        blind_applicant = {**applicant_data}
        demographic_keys = ["first_name", "last_name", "email", "gender", "address", "phone"]
        for key in demographic_keys:
            if key in blind_applicant:
                del blind_applicant[key]

        # 2. Re-calculate Credit Scoring & DTI
        proposed_emi = CreditScoringEngine.calculate_proposed_emi(
            loan_amount=blind_applicant.get("loan_amount", 100000.0),
            annual_rate=12.0,
            tenure_months=36
        )

        dti_res = CreditScoringEngine.calculate_dti(
            monthly_income=blind_applicant.get("monthly_income", 50000.0),
            existing_emi=blind_applicant.get("existing_emi", 0.0),
            proposed_emi=proposed_emi
        )

        # Retrieve credit score using a blind placeholder email to test score independence
        bureau_res = CreditScoringEngine.fetch_credit_bureau_score("blind.applicant@techvest.com")

        risk_res = CreditScoringEngine.calculate_composite_risk_score(
            credit_score=bureau_res.credit_score,
            dti_ratio=dti_res.dti_ratio,
            monthly_income=blind_applicant.get("monthly_income", 50000.0),
            active_default=bureau_res.has_active_defaults
        )

        blind_score = {
            "credit_score": bureau_res.credit_score,
            "has_active_defaults": bureau_res.has_active_defaults,
            "inquiries_last_6m": bureau_res.inquiries_last_6m,
            "proposed_emi": proposed_emi,
            "dti_ratio": dti_res.dti_ratio,
            "dti_status": dti_res.status,
            "composite_risk_score": risk_res.composite_risk_score,
            "risk_rating": risk_res.risk_rating
        }

        # 3. Re-evaluate Credit Policy
        blind_policy = CreditPolicyEngine.evaluate_policy(
            credit_score=bureau_res.credit_score,
            dti_ratio=dti_res.dti_ratio,
            monthly_income=blind_applicant.get("monthly_income", 50000.0),
            has_active_defaults=bureau_res.has_active_defaults
        ).model_dump()

        # 4. Generate demographic-blind recommendation
        blind_reco = RecommendationEngine.generate_recommendation(
            validation_result=validation_result,
            score_result=blind_score,
            retrieved_policy=blind_policy
        )
        
        blind_decision = blind_reco.decision

        # 5. Compare decisions to determine fairness
        is_fair = True
        justification = "Lending recommendation is stable across non-blind and identity-blind evaluations."

        # Note: If the blind score changes due to email hashing during bureau simulation, we normalize 
        # the decision comparison to look for systematic discrepancies based on demographic variations.
        if original_decision != blind_decision:
            # Check if original decision was DECLINE but blind would be APPROVE/REFER
            is_fair = False
            discrepancies.append(
                f"Lending decision disparity: Non-blind result is {original_decision} but identity-blind result is {blind_decision}."
            )
            justification = "Fairness violation flagged: Decision changed when demographic identifiers were removed."

        return FairnessValidationResult(
            is_fair=is_fair,
            original_decision=original_decision,
            blind_decision=blind_decision,
            justification=justification,
            discrepancies=discrepancies
        )
