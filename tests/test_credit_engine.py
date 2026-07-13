import pytest
from backend.tools.credit_engine import CreditScoringEngine

def test_proposed_emi_calculation():
    # Principal 100,000, 12% annual interest (1% monthly), 36 months
    # Formula: 100000 * 0.01 * (1.01)^36 / ((1.01)^36 - 1)
    # Expected EMI is ~3321.43
    emi = CreditScoringEngine.calculate_proposed_emi(100000.0, annual_rate=12.0, tenure_months=36)
    assert abs(emi - 3321.43) < 1.00

def test_dti_ratio_and_status_checks():
    # Stated Gross monthly income = 50,000
    # Case 1: Excellent (DTI <= 40%) -> PASSED
    res_passed = CreditScoringEngine.calculate_dti(
        monthly_income=50000.0,
        existing_emi=5000.0,
        proposed_emi=10000.0
    )
    assert res_passed.dti_ratio == 0.30
    assert res_passed.status == "PASSED"

    # Case 2: Borderline (DTI 40.1% to 45%) -> REFER
    res_refer = CreditScoringEngine.calculate_dti(
        monthly_income=50000.0,
        existing_emi=10000.0,
        proposed_emi=11000.0
    )
    assert res_refer.dti_ratio == 0.42
    assert res_refer.status == "REFER"

    # Case 3: Excessive (DTI > 45%) -> FAILED
    res_failed = CreditScoringEngine.calculate_dti(
        monthly_income=50000.0,
        existing_emi=10000.0,
        proposed_emi=15000.0
    )
    assert res_failed.dti_ratio == 0.50
    assert res_failed.status == "FAILED"

def test_credit_bureau_determinisim():
    # Clear Approve
    res_approve = CreditScoringEngine.fetch_credit_bureau_score("clear.approve@example.com")
    assert res_approve.credit_score == 800
    assert res_approve.has_active_defaults is False

    # Borderline Refer
    res_refer = CreditScoringEngine.fetch_credit_bureau_score("borderline.refer@example.com")
    assert res_refer.credit_score == 680

    # Low Score decline
    res_decline = CreditScoringEngine.fetch_credit_bureau_score("declined.lowscore@example.com")
    assert res_decline.credit_score == 550

    # Default
    res_default = CreditScoringEngine.fetch_credit_bureau_score("default@example.com")
    assert res_default.has_active_defaults is True

def test_composite_risk_scoring():
    # Case 1: Low risk applicant (Score 800, DTI 0.25, Income 120k, No default)
    res_low = CreditScoringEngine.calculate_composite_risk_score(
        credit_score=800,
        dti_ratio=0.25,
        monthly_income=120000.0,
        active_default=False
    )
    assert res_low.risk_rating == "LOW"
    assert res_low.composite_risk_score == 0.0

    # Case 2: High risk default
    res_default = CreditScoringEngine.calculate_composite_risk_score(
        credit_score=780,
        dti_ratio=0.20,
        monthly_income=90000.0,
        active_default=True
    )
    assert res_default.risk_rating == "HIGH"
    assert res_default.composite_risk_score == 100.0

    # Case 3: Medium Risk applicant
    res_med = CreditScoringEngine.calculate_composite_risk_score(
        credit_score=680,  # 20 risk points
        dti_ratio=0.42,    # 20 risk points
        monthly_income=40000.0, # 20 risk points
        active_default=False
    )
    assert res_med.risk_rating == "HIGH"  # sum = 60 points (> 50 is HIGH risk rating)
