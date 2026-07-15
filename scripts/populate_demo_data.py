import os
import sys
import uuid
import random
from datetime import datetime, timedelta

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database.session import SessionLocal, Base, engine
from backend.models.db_models import (
    Applicant, Application, Document, PolicyResult, Recommendation, HumanDecision, AuditLog
)

def populate_mock_data():
    print("Initializing database connection...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Clean previous demo entries if they exist
    print("Clearing any existing demo records...")
    db.query(AuditLog).filter(AuditLog.performed_by.in_(["LANGGRAPH_ENGINE", "DEMO_SEEDED"])).delete(synchronize_session=False)
    db.query(HumanDecision).filter(HumanDecision.underwriter_email.like("%@demo.com")).delete(synchronize_session=False)
    db.query(Recommendation).filter(Recommendation.reasoning.like("%demo%")).delete(synchronize_session=False)
    db.query(PolicyResult).filter(PolicyResult.rule_cited.like("%demo%")).delete(synchronize_session=False)
    db.query(Document).filter(Document.file_path.like("%demo%")).delete(synchronize_session=False)
    db.query(Application).filter(Application.loan_purpose.like("%demo%")).delete(synchronize_session=False)
    db.query(Applicant).filter(Applicant.email.like("%@demo.com")).delete(synchronize_session=False)
    db.commit()

    print("Generating 30 custom demographic applications...")
    
    # 30% approved (9), 40% refer (12), 30% decline (9)
    approved_list = [
        ("John", "Smith", 75000.0, 5000.0, 150000.0, 780, 0.18, "john.smith@demo.com"),
        ("Alice", "Johnson", 82000.0, 3000.0, 200000.0, 795, 0.12, "alice.johnson@demo.com"),
        ("Robert", "Lee", 95000.0, 12000.0, 250000.0, 810, 0.22, "robert.lee@demo.com"),
        ("Sarah", "Davis", 70000.0, 4000.0, 120000.0, 765, 0.15, "sarah.davis@demo.com"),
        ("Emily", "Watson", 68000.0, 2000.0, 100000.0, 755, 0.10, "emily.watson@demo.com"),
        ("Michael", "Brown", 88000.0, 8000.0, 180000.0, 788, 0.17, "michael.brown@demo.com"),
        ("Sophia", "Carter", 110000.0, 15000.0, 300000.0, 825, 0.25, "sophia.carter@demo.com"),
        ("James", "Wilson", 72000.0, 4500.0, 140000.0, 772, 0.16, "james.wilson@demo.com"),
        ("Grace", "Taylor", 80000.0, 6000.0, 160000.0, 790, 0.19, "grace.taylor@demo.com")
    ]
    
    refer_list = [
        ("Nancy", "Wheeler", 50000.0, 0.0, 350000.0, 645, 0.24, "nancy.wheeler@demo.com"),
        ("Peter", "Parker", 40000.0, 12000.0, 80000.0, 620, 0.38, "peter.parker@demo.com"),
        ("Clark", "Kent", 55000.0, 5000.0, 250000.0, 630, 0.28, "clark.kent@demo.com"),
        ("Bruce", "Wayne", 35000.0, 4000.0, 150000.0, 615, 0.35, "bruce.wayne@demo.com"),
        ("Tony", "Stark", 52000.0, 2000.0, 220000.0, 640, 0.26, "tony.stark@demo.com"),
        ("Diana", "Prince", 48000.0, 3500.0, 180000.0, 628, 0.29, "diana.prince@demo.com"),
        ("Barry", "Allen", 45000.0, 8000.0, 120000.0, 610, 0.36, "barry.allen@demo.com"),
        ("Arthur", "Curry", 53000.0, 4500.0, 200000.0, 632, 0.27, "arthur.curry@demo.com"),
        ("Hal", "Jordan", 46000.0, 3000.0, 160000.0, 618, 0.32, "hal.jordan@demo.com"),
        ("Selina", "Kyle", 42000.0, 2500.0, 140000.0, 622, 0.33, "selina.kyle@demo.com"),
        ("Steve", "Rogers", 49000.0, 6000.0, 170000.0, 635, 0.31, "steve.rogers@demo.com"),
        ("Wanda", "Maximoff", 47000.0, 5000.0, 150000.0, 625, 0.30, "wanda.maximoff@demo.com")
    ]
    
    decline_list = [
        ("Loki", "Laufeyson", 40000.0, 15000.0, 150000.0, 540, 0.55, "loki.laufeyson@demo.com"),
        ("Arthur", "Dent", 28000.0, 12000.0, 100000.0, 520, 0.62, "arthur.dent@demo.com"),
        ("Charles", "Xavier", 32000.0, 10000.0, 120000.0, 510, 0.58, "charles.xavier@demo.com"),
        ("Erik", "Lehnsherr", 35000.0, 14000.0, 130000.0, 530, 0.60, "erik.lehnsherr@demo.com"),
        ("Walter", "White", 25000.0, 8000.0, 100000.0, 480, 0.52, "walter.white@demo.com"),
        ("Jesse", "Pinkman", 22000.0, 6000.0, 90000.0, 490, 0.49, "jesse.pinkman@demo.com"),
        ("Saul", "Goodman", 38000.0, 18000.0, 110000.0, 550, 0.61, "saul.goodman@demo.com"),
        ("Gus", "Fring", 30000.0, 11000.0, 140000.0, 505, 0.56, "gus.fring@demo.com"),
        ("Mike", "Ehrmantraut", 27000.0, 9000.0, 105000.0, 495, 0.51, "mike.ehrmantraut@demo.com")
    ]
    
    all_demographics = [
        ("APPROVED", approved_list),
        ("REFER", refer_list),
        ("DECLINED", decline_list)
    ]
    
    # Track distributions
    total_added = 0
    
    for outcome, applicants in all_demographics:
        for idx, (first, last, monthly_inc, emi, loan, score, dti, email) in enumerate(applicants):
            # Generate timestamps distributed over the last 7 days
            days_ago = random.randint(0, 6)
            hours_ago = random.randint(1, 23)
            created_dt = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
            
            # Create applicant
            applicant = Applicant(
                first_name=first,
                last_name=last,
                dob="1992-06-15",
                email=email,
                monthly_income=monthly_inc,
                existing_emi=emi,
                created_at=created_dt
            )
            db.add(applicant)
            db.commit()
            db.refresh(applicant)
            
            # Create application
            application = Application(
                applicant_id=applicant.id,
                loan_amount=loan,
                loan_purpose="Business expansion (demo)",
                status=outcome,
                credit_score=score,
                dti_ratio=dti,
                created_at=created_dt,
                updated_at=created_dt
            )
            db.add(application)
            db.commit()
            db.refresh(application)
            
            # Create document files
            doc_types = ["PAN", "Aadhaar", "Salary Slip", "Bank Statement"]
            for dtype in doc_types:
                doc = Document(
                    application_id=application.id,
                    document_type=dtype,
                    file_path=f"./uploads/{application.id}_{dtype.lower().replace(' ', '_')}.png (demo)",
                    is_valid=True,
                    validation_result={
                        "is_valid": True,
                        "confidence": 0.96,
                        "name": f"{first} {last}".upper(),
                        "dob": "15/06/1992"
                    },
                    created_at=created_dt
                )
                db.add(doc)
            
            # Create Policy Results
            policies = [
                ("Credit Check", "PASSED" if score >= 600 else "FAILED", f"Score check is {score} (demo)"),
                ("DTI Check", "PASSED" if dti < 0.35 else "REFER" if dti <= 0.45 else "FAILED", f"Ratio check is {dti:.2%} (demo)"),
                ("KYC Check", "PASSED", "Government documents verified (demo)")
            ]
            for pname, pstatus, rule in policies:
                pr = PolicyResult(
                    application_id=application.id,
                    policy_name=pname,
                    status=pstatus,
                    rule_cited=rule,
                    created_at=created_dt
                )
                db.add(pr)
                
            # Create AI Recommendation
            ai_dec = "APPROVE" if outcome == "APPROVED" else "REFER" if outcome == "REFER" else "DECLINE"
            reco = Recommendation(
                application_id=application.id,
                decision=ai_dec,
                reasoning=f"Seeded demo recommendation: {first} {last} DTI {dti:.2%} Credit Score {score}",
                composite_score=0.92 if outcome == "APPROVED" else 0.65 if outcome == "REFER" else 0.25,
                fairness_passed=True,
                created_at=created_dt
            )
            db.add(reco)
            db.commit()
            db.refresh(reco)
            
            # Create Human Decision
            human_dec = "APPROVED" if outcome == "APPROVED" else "REFER" if outcome == "REFER" else "DECLINED"
            hd = HumanDecision(
                application_id=application.id,
                decision=human_dec,
                comments=f"Seeded underwriter review. AI recommended {ai_dec} decision.",
                underwriter_email="underwriter@demo.com",
                timestamp=created_dt + timedelta(minutes=random.randint(5, 45))
            )
            db.add(hd)
            
            # Create complete Audit execution logs
            complete_trace = {
                "applicant": {
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "dob": "1992-06-15",
                    "monthly_income": monthly_inc,
                    "existing_emi": emi,
                    "loan_amount": loan,
                    "loan_purpose": "Business expansion (demo)"
                },
                "documents": [
                    {"document_type": d, "file_path": f"./uploads/{application.id}_{d.lower()}.png"} for d in doc_types
                ],
                "validation_result": {"is_complete": True},
                "retrieved_policy": {"matches": [{"clause_cited": "General Credit Policy (demo)", "status": "PASSED", "reasoning": "Score matches threshold."}]},
                "score": {"credit_score": score, "dti_ratio": dti},
                "recommendation": {"decision": ai_dec, "composite_score": 0.92 if outcome == "APPROVED" else 0.65 if outcome == "REFER" else 0.25, "reasoning": "Demo calculation"},
                "fairness_result": {"fairness_passed": True},
                "metadata": {
                    "node_timings": {
                        "loan_intake_node": 15.2,
                        "document_validation_node": 95.8,
                        "policy_retrieval_node": 45.1,
                        "credit_scoring_node": 32.4,
                        "recommendation_node": 88.6,
                        "fairness_check_node": 35.2,
                        "audit_logging_node": 10.3
                    },
                    "execution_path": [
                        "loan_intake_node",
                        "document_validation_node",
                        "policy_retrieval_node",
                        "credit_scoring_node",
                        "recommendation_node",
                        "fairness_check_node",
                        "audit_logging_node"
                    ],
                    "token_usage": {
                        "input_tokens": random.randint(800, 1200),
                        "output_tokens": random.randint(200, 400),
                        "total_tokens": random.randint(1000, 1600)
                    }
                }
            }
            
            audit = AuditLog(
                application_id=application.id,
                action="WORKFLOW_EXECUTION",
                performed_by="LANGGRAPH_ENGINE",
                details=complete_trace,
                timestamp=created_dt
            )
            db.add(audit)
            db.commit()
            
            total_added += 1

    print(f"Database seeding complete. Successfully registered {total_added} applications!")
    print("APPROVED: 9 (30%) | REFER: 12 (40%) | DECLINED/REJECTED: 9 (30%)")
    db.close()

if __name__ == "__main__":
    populate_mock_data()
