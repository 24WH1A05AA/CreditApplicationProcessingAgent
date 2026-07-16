import os
import json
import hashlib
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from backend.utils.logging import logger

# ================= Structured Pydantic Output Models =================

class DTIResult(BaseModel):
    monthly_income: float = Field(..., description="Stated gross monthly income in INR")
    existing_emi: float = Field(..., description="Existing EMIs in INR")
    proposed_emi: float = Field(..., description="Proposed EMI in INR")
    dti_ratio: float = Field(..., description="Calculated DTI ratio (0.0 to 1.0)")
    status: str = Field(..., description="PASSED, REFER, FAILED")

class CreditBureauResult(BaseModel):
    credit_score: int = Field(..., description="Bureau credit score (300 to 900)")
    has_active_defaults: bool = Field(..., description="True if applicant has active default in last 12m")
    inquiries_last_6m: int = Field(..., description="Number of credit inquiries in last 6 months")
    historical_scores: List[int] = Field(default_factory=list)
    payment_history_pct: float = Field(98.5)
    credit_mix: str = Field("Good mix")
    credit_age_years: float = Field(5.0)

class RiskScoreResult(BaseModel):
    credit_score: int
    dti_ratio: float
    monthly_income: float
    active_default: bool
    composite_risk_score: float = Field(..., description="Composite Risk Score (0.0 to 100.0, lower is better)")
    risk_rating: str = Field(..., description="LOW, MEDIUM, HIGH")


# ================= Policy Loader Utility =================

def load_scoring_policy() -> Dict[str, Any]:
    policy_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "scoring_policy.json"
    )
    
    # Standard fallback defaults matching the specifications
    default_policy = {
        "dti_thresholds": {"passed": 0.40, "refer": 0.45},
        "credit_score_thresholds": {"excellent": 750, "good": 700, "fair": 650, "poor": 600},
        "risk_points": {
            "credit_score": {"excellent": 0, "good": 10, "fair": 20, "poor": 30, "very_poor": 35},
            "dti": {"excellent": 0, "good": 10, "fair": 20, "poor": 35},
            "income": {"excellent": 0, "good": 10, "fair": 20, "poor": 30}
        },
        "dti_boundaries": [0.30, 0.40, 0.45],
        "income_boundaries": [100000.0, 50000.0, 25000.0],
        "risk_rating_boundaries": {"low": 25.0, "medium": 50.0}
    }
    
    if os.path.exists(policy_path):
        try:
            with open(policy_path, "r") as f:
                logger.info("Loaded custom credit scoring policy from %s", policy_path)
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load custom scoring policy file: %s. Using default policy.", str(e))
            
    return default_policy


# ================= Core Implementations =================

class CreditScoringEngine:
    @staticmethod
    def calculate_proposed_emi(
        loan_amount: float,
        annual_rate: float = 12.0,
        tenure_months: int = 36
    ) -> float:
        """
        Calculates the monthly EMI for the proposed loan amount.
        """
        r = (annual_rate / 12.0) / 100.0
        n = tenure_months
        if r == 0:
            return loan_amount / n
        return loan_amount * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)

    @staticmethod
    def calculate_dti(
        monthly_income: float,
        existing_emi: float,
        proposed_emi: float
    ) -> DTIResult:
        """
        Calculates Debt-to-Income (DTI) ratio and sets status based on credit policy.
        """
        policy = load_scoring_policy()
        thresholds = policy.get("dti_thresholds", {"passed": 0.40, "refer": 0.45})
        
        if monthly_income <= 0:
            return DTIResult(
                monthly_income=monthly_income,
                existing_emi=existing_emi,
                proposed_emi=proposed_emi,
                dti_ratio=1.0,
                status="FAILED"
            )

        total_debt = existing_emi + proposed_emi
        dti_ratio = total_debt / monthly_income
        
        # Policy evaluation status mapping using loaded policy
        if dti_ratio <= thresholds.get("passed", 0.40):
            status = "PASSED"
        elif dti_ratio <= thresholds.get("refer", 0.45):
            status = "REFER"
        else:
            status = "FAILED"

        return DTIResult(
            monthly_income=monthly_income,
            existing_emi=existing_emi,
            proposed_emi=proposed_emi,
            dti_ratio=round(dti_ratio, 4),
            status=status
        )

    @staticmethod
    def fetch_credit_bureau_score(email: str) -> CreditBureauResult:
        """
        Fetches the credit score and history from the credit bureau.
        """
        email_clean = email.strip().lower()
        
        if "clear.approve" in email_clean:
            return CreditBureauResult(
                credit_score=800,
                has_active_defaults=False,
                inquiries_last_6m=0,
                historical_scores=[790, 792, 795, 798, 799, 800],
                payment_history_pct=99.8,
                credit_mix="Excellent mix (secured home loan + credit card)",
                credit_age_years=8.5
            )
        elif "borderline.refer" in email_clean:
            return CreditBureauResult(
                credit_score=680,
                has_active_defaults=False,
                inquiries_last_6m=2,
                historical_scores=[685, 680, 678, 682, 685, 680],
                payment_history_pct=96.5,
                credit_mix="Good mix (secured auto loan + unsecured card)",
                credit_age_years=4.2
            )
        elif "declined.lowscore" in email_clean or "decline" in email_clean:
            return CreditBureauResult(
                credit_score=550,
                has_active_defaults=False,
                inquiries_last_6m=4,
                historical_scores=[580, 570, 565, 560, 555, 550],
                payment_history_pct=88.2,
                credit_mix="Fair mix (unsecured loans/cards)",
                credit_age_years=2.1
            )
        elif "default" in email_clean:
            return CreditBureauResult(
                credit_score=710,
                has_active_defaults=True,
                inquiries_last_6m=1,
                historical_scores=[725, 720, 715, 705, 708, 710],
                payment_history_pct=92.1,
                credit_mix="Good mix (secured auto loan + unsecured card)",
                credit_age_years=5.0
            )
        
        hasher = hashlib.md5(email_clean.encode())
        hash_val = int(hasher.hexdigest(), 16)
        credit_score = 600 + (hash_val % 251)
        inquiries = hash_val % 6
        has_default = (hash_val % 20) == 0

        # Generate a simulated historical score list (last 6 months)
        hist_scores = []
        curr_score = credit_score
        for i in range(6):
            variance = ((hash_val + i) % 15) - 7
            hist_scores.append(max(300, min(900, curr_score - variance * (6 - i))))
            
        payment_pct = 90.0 + (hash_val % 101) / 10.0
        age = round(1.0 + (hash_val % 15) + (hash_val % 10)/10.0, 1)
        
        mixes = [
            "Poor mix (unsecured cards only)",
            "Fair mix (unsecured loans/cards)",
            "Good mix (secured auto loan + unsecured card)",
            "Excellent mix (secured home loan + credit card)"
        ]
        mix = mixes[hash_val % len(mixes)]

        logger.info("Bureau credit score fetched for %s: %d", email, credit_score)
        return CreditBureauResult(
            credit_score=credit_score,
            has_active_defaults=has_default,
            inquiries_last_6m=inquiries,
            historical_scores=hist_scores,
            payment_history_pct=payment_pct,
            credit_mix=mix,
            credit_age_years=age
        )

    @staticmethod
    def calculate_composite_risk_score(
        credit_score: int,
        dti_ratio: float,
        monthly_income: float,
        active_default: bool
    ) -> RiskScoreResult:
        """
        Computes a composite Risk Score from 0 to 100 (lower is better) using configurable policy weights.
        """
        policy = load_scoring_policy()
        
        # Load score thresholds and weights from policy
        score_thresh = policy.get("credit_score_thresholds", {"excellent": 750, "good": 700, "fair": 650, "poor": 600})
        pts_config = policy.get("risk_points", {})
        
        dti_bounds = policy.get("dti_boundaries", [0.30, 0.40, 0.45])
        inc_bounds = policy.get("income_boundaries", [100000.0, 50000.0, 25000.0])
        rating_bounds = policy.get("risk_rating_boundaries", {"low": 25.0, "medium": 50.0})

        risk_points = 0
        
        # 1. Credit Score Risk Points (Max 35 points)
        cs_pts = pts_config.get("credit_score", {})
        if credit_score >= score_thresh.get("excellent", 750):
            risk_points += cs_pts.get("excellent", 0)
        elif credit_score >= score_thresh.get("good", 700):
            risk_points += cs_pts.get("good", 10)
        elif credit_score >= score_thresh.get("fair", 650):
            risk_points += cs_pts.get("fair", 20)
        elif credit_score >= score_thresh.get("poor", 600):
            risk_points += cs_pts.get("poor", 30)
        else:
            risk_points += cs_pts.get("very_poor", 35)

        # 2. DTI Ratio Risk Points (Max 35 points)
        dti_pts = pts_config.get("dti", {})
        if dti_ratio <= dti_bounds[0]:
            risk_points += dti_pts.get("excellent", 0)
        elif dti_ratio <= dti_bounds[1]:
            risk_points += dti_pts.get("good", 10)
        elif dti_ratio <= dti_bounds[2]:
            risk_points += dti_pts.get("fair", 20)
        else:
            risk_points += dti_pts.get("poor", 35)

        # 3. Monthly Income Risk Points (Max 30 points)
        inc_pts = pts_config.get("income", {})
        if monthly_income >= inc_bounds[0]:
            risk_points += inc_pts.get("excellent", 0)
        elif monthly_income >= inc_bounds[1]:
            risk_points += inc_pts.get("good", 10)
        elif monthly_income >= inc_bounds[2]:
            risk_points += inc_pts.get("fair", 20)
        else:
            risk_points += inc_pts.get("poor", 30)

        # 4. Immediate high risk multiplier if defaults are active
        if active_default:
            composite_risk_score = 100.0
            risk_rating = "HIGH"
        else:
            composite_risk_score = float(risk_points)
            
            # Map rating using loaded boundaries
            if composite_risk_score <= rating_bounds.get("low", 25.0):
                risk_rating = "LOW"
            elif composite_risk_score <= rating_bounds.get("medium", 50.0):
                risk_rating = "MEDIUM"
            else:
                risk_rating = "HIGH"

        return RiskScoreResult(
            credit_score=credit_score,
            dti_ratio=dti_ratio,
            monthly_income=monthly_income,
            active_default=active_default,
            composite_risk_score=composite_risk_score,
            risk_rating=risk_rating
        )
