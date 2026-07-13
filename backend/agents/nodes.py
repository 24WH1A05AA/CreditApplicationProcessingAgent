from typing import Dict, Any, List, Optional
from backend.agents.state import UnderwritingState
from backend.tools.document_processor import DocumentParser, DocumentValidator, ConsistencyChecker
from backend.tools.credit_engine import CreditScoringEngine
from backend.tools.policy_engine import CreditPolicyEngine
from backend.tools.recommendation_engine import RecommendationEngine
from backend.tools.fairness_checker import FairnessChecker
from backend.database.session import SessionLocal
from backend.database.repository import (
    applicant_repo,
    application_repo,
    document_repo,
    policy_result_repo,
    recommendation_repo,
    human_decision_repo,
    audit_log_repo
)
from backend.models.db_models import Document, Application
from backend.utils.logging import logger

class WorkflowNodes:
    """
    Encapsulates all node functions for the LangGraph underwriting workflow.
    Each method represents a distinct node in the state graph.
    """

    @staticmethod
    def loan_intake(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 1: Loan Intake
        Accepts stated applicant info and registers the initial application in the database.
        """
        logger.info("LangGraph Node: Executing Loan Intake...")
        app_data = state["applicant"]
        docs_list = state.get("documents", [])

        db = SessionLocal()
        try:
            # 1. Ensure applicant exists in DB, or create one
            db_applicant = applicant_repo.get_by_email(db, app_data["email"])
            if not db_applicant:
                db_applicant = applicant_repo.create(db, obj_in={
                    "first_name": app_data.get("first_name", ""),
                    "last_name": app_data.get("last_name", ""),
                    "email": app_data["email"],
                    "dob": app_data.get("dob", ""),
                    "monthly_income": app_data.get("monthly_income", 0.0),
                    "existing_emi": app_data.get("existing_emi", 0.0)
                })
            
            # 2. Register a new Loan Application in DB
            db_application = application_repo.create(db, obj_in={
                "applicant_id": db_applicant.id,
                "loan_amount": app_data.get("loan_amount", 100000.0),
                "loan_purpose": app_data.get("loan_purpose", "Personal Loan"),
                "status": "INTAKE",
                "credit_score": None,
                "dti_ratio": None
            })

            # 3. Associate documents with the application in DB
            for doc in docs_list:
                document_repo.create(db, obj_in={
                    "application_id": db_application.id,
                    "document_type": doc["document_type"],
                    "file_path": doc["file_path"],
                    "is_valid": None,
                    "validation_result": None
                })

            # Update the applicant dict in state to store generated IDs
            updated_applicant = {**app_data, "id": db_applicant.id, "application_id": db_application.id}
            
            return {
                "applicant": updated_applicant,
                "metadata": {**state.get("metadata", {}), "intake_completed": True}
            }
        except Exception as e:
            logger.error("Failed in Loan Intake node: %s", str(e))
            raise e
        finally:
            db.close()

    @staticmethod
    def document_validation(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 2: Document Validation
        Performs OCR/parsing extraction, validate fields, and cross-checks documents.
        """
        logger.info("LangGraph Node: Executing Document Validation...")
        docs_list = state.get("documents", [])
        applicant_data = state["applicant"]
        
        parsed_docs = []
        validation_results = {}
        missing_docs = ["PAN", "Aadhaar", "Salary Slip", "Bank Statement"]

        # 1. Parse each document
        for doc in docs_list:
            doc_type = doc["document_type"]
            path = doc["file_path"]
            
            try:
                if path.lower().endswith(".pdf"):
                    parsed = DocumentParser.parse_pdf(path, doc_type)
                else:
                    parsed = DocumentParser.parse_image(path, doc_type)
                
                parsed_docs.append(parsed)
                if doc_type in missing_docs:
                    missing_docs.remove(doc_type)
            except Exception as pe:
                logger.warning("Failed parsing document type %s: %s", doc_type, str(pe))

        # 2. Validate extracted text format
        pan_res, aadhaar_res, salary_res, bank_res = None, None, None, None
        
        for p_doc in parsed_docs:
            if p_doc.document_type == "PAN":
                pan_res = DocumentValidator.validate_pan(p_doc)
                validation_results["pan"] = pan_res.model_dump()
            elif p_doc.document_type == "Aadhaar":
                aadhaar_res = DocumentValidator.validate_aadhaar(p_doc)
                validation_results["aadhaar"] = aadhaar_res.model_dump()
            elif p_doc.document_type == "Salary Slip":
                salary_res = DocumentValidator.validate_salary_slip(p_doc)
                validation_results["salary_slip"] = salary_res.model_dump()
            elif p_doc.document_type == "Bank Statement":
                bank_res = DocumentValidator.validate_bank_statement(p_doc)
                validation_results["bank_statement"] = bank_res.model_dump()

        # 3. Check consistency across all parsed files
        consistency_res = ConsistencyChecker.check_identity_and_income_consistency(
            pan=pan_res,
            aadhaar=aadhaar_res,
            salary_slip=salary_res,
            bank_statement=bank_res,
            app_data=applicant_data
        )

        validation_results["is_complete"] = len(missing_docs) == 0
        validation_results["missing_documents"] = missing_docs
        validation_results["consistency"] = consistency_res.model_dump()

        # Update document validation status in DB
        db = SessionLocal()
        try:
            app_id = applicant_data.get("application_id")
            if app_id:
                db_docs = document_repo.get_by_application(db, app_id)
                for db_doc in db_docs:
                    dtype = db_doc.document_type
                    # Find parsed document
                    p_doc = next((p for p in parsed_docs if p.document_type == dtype), None)
                    if p_doc:
                        if dtype == "PAN" and pan_res:
                            db_doc.is_valid = pan_res.is_valid
                            db_doc.validation_result = pan_res.model_dump()
                        elif dtype == "Aadhaar" and aadhaar_res:
                            db_doc.is_valid = aadhaar_res.is_valid
                            db_doc.validation_result = aadhaar_res.model_dump()
                        elif dtype == "Salary Slip" and salary_res:
                            db_doc.is_valid = salary_res.is_valid
                            db_doc.validation_result = salary_res.model_dump()
                        elif dtype == "Bank Statement" and bank_res:
                            db_doc.is_valid = bank_res.is_valid
                            db_doc.validation_result = bank_res.model_dump()
                
                # Also update application status
                db_app = application_repo.get(db, app_id)
                if db_app:
                    db_app.status = "DOC_VALIDATION"
                db.commit()
        except Exception as dbe:
            logger.warning("Could not update document statuses in DB: %s", str(dbe))
        finally:
            db.close()

        return {"validation_result": validation_results}

    @staticmethod
    def policy_retrieval(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 3: Policy Retrieval
        Retrieves matching underwriting clauses and citations via the RAG pipeline.
        """
        logger.info("LangGraph Node: Executing Policy Retrieval...")
        score_data = state.get("score") or {}
        applicant_data = state["applicant"]
        
        # Extract evaluation params
        credit_score = score_data.get("credit_score", 700)
        dti_ratio = score_data.get("dti_ratio", 0.35)
        monthly_income = applicant_data.get("monthly_income", 50000.0)
        
        # Check active defaults in validation consistency or score records
        val_res = state.get("validation_result") or {}
        has_defaults = False
        if val_res.get("bank_statement", {}).get("error_message"):
            has_defaults = "default" in val_res["bank_statement"]["error_message"].lower()

        # Run the credit policy evaluation engine using RAG matching
        policy_eval = CreditPolicyEngine.evaluate_policy(
            credit_score=credit_score,
            dti_ratio=dti_ratio,
            monthly_income=monthly_income,
            has_active_defaults=has_defaults
        )

        return {"retrieved_policy": policy_eval.model_dump()}

    @staticmethod
    def credit_scoring(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 4: Credit Scoring
        Fetches bureau scores, computes DTI ratios and the composite risk score.
        """
        logger.info("LangGraph Node: Executing Credit Scoring...")
        applicant_data = state["applicant"]
        
        # 1. Calculate proposed EMI
        proposed_emi = CreditScoringEngine.calculate_proposed_emi(
            loan_amount=applicant_data.get("loan_amount", 100000.0),
            annual_rate=12.0,
            tenure_months=36
        )

        # 2. Compute DTI ratio
        dti_res = CreditScoringEngine.calculate_dti(
            monthly_income=applicant_data.get("monthly_income", 50000.0),
            existing_emi=applicant_data.get("existing_emi", 0.0),
            proposed_emi=proposed_emi
        )

        # 3. Fetch credit bureau score
        bureau_res = CreditScoringEngine.fetch_credit_bureau_score(applicant_data["email"])

        # 4. Calculate composite risk score
        risk_res = CreditScoringEngine.calculate_composite_risk_score(
            credit_score=bureau_res.credit_score,
            dti_ratio=dti_res.dti_ratio,
            monthly_income=applicant_data.get("monthly_income", 50000.0),
            active_default=bureau_res.has_active_defaults
        )

        score_details = {
            "credit_score": bureau_res.credit_score,
            "has_active_defaults": bureau_res.has_active_defaults,
            "inquiries_last_6m": bureau_res.inquiries_last_6m,
            "proposed_emi": proposed_emi,
            "dti_ratio": dti_res.dti_ratio,
            "dti_status": dti_res.status,
            "composite_risk_score": risk_res.composite_risk_score,
            "risk_rating": risk_res.risk_rating
        }

        # Update application table with score information
        db = SessionLocal()
        try:
            app_id = applicant_data.get("application_id")
            if app_id:
                db_app = application_repo.get(db, app_id)
                if db_app:
                    db_app.credit_score = bureau_res.credit_score
                    db_app.dti_ratio = dti_res.dti_ratio
                    db_app.status = "EVALUATION"
                    db.commit()
        except Exception as dbe:
            logger.warning("Could not update risk score in DB: %s", str(dbe))
        finally:
            db.close()

        return {"score": score_details}

    @staticmethod
    def recommendation(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 5: Recommendation Generation
        Synthesizes validation results, scoring details, and policies to recommend APPROVE/DECLINE/REFER.
        """
        logger.info("LangGraph Node: Executing Recommendation...")
        val_res = state.get("validation_result") or {}
        score_res = state.get("score") or {}
        policy_res = state.get("retrieved_policy") or {}
        applicant_data = state["applicant"]
        app_id = applicant_data.get("application_id")

        # Call structured recommendation engine
        reco_output = RecommendationEngine.generate_recommendation(
            validation_result=val_res,
            score_result=score_res,
            retrieved_policy=policy_res
        )

        reco_details = reco_output.model_dump()

        # Save results in the database
        db = SessionLocal()
        try:
            if app_id:
                # 1. Create Policy Results
                for m in policy_res.get("matches", []):
                    policy_result_repo.create(db, obj_in={
                        "application_id": app_id,
                        "policy_name": m.get("parameter", "General"),
                        "status": m.get("status", "PASSED"),
                        "details": m.get("reasoning"),
                        "rule_cited": m.get("clause_cited")
                    })
                
                # 2. Create Recommendation
                recommendation_repo.create(db, obj_in={
                    "application_id": app_id,
                    "decision": reco_output.decision,
                    "reasoning": "; ".join(reco_output.reasons),
                    "composite_score": score_res.get("composite_risk_score", 0.0),
                    "fairness_passed": None
                })

                # 3. Update application status
                db_app = application_repo.get(db, app_id)
                if db_app:
                    db_app.status = "UNDERWRITTEN"
                db.commit()
        except Exception as dbe:
            logger.warning("Could not persist recommendations in DB: %s", str(dbe))
        finally:
            db.close()

        return {"recommendation": reco_details}

    @staticmethod
    def fairness_check(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 6: Fairness Check
        Validates decision parity using demographic-blind parameter checks.
        """
        logger.info("LangGraph Node: Executing Fairness Check...")
        score_res = state.get("score") or {}
        reco_res = state.get("recommendation") or {}
        applicant_data = state["applicant"]
        app_id = applicant_data.get("application_id")

        # Call the demographic-blind fairness checker
        fairness_res = FairnessChecker.validate_fairness(
            applicant_data=applicant_data,
            validation_result=state.get("validation_result") or {},
            original_score=score_res,
            original_policy=state.get("retrieved_policy") or {},
            original_decision=reco_res.get("decision", "REFER")
        )

        fairness_details = fairness_res.model_dump()

        # Update recommendation fairness outcome in DB
        db = SessionLocal()
        try:
            if app_id:
                db_reco = recommendation_repo.get_by_application(db, app_id)
                if db_reco:
                    db_reco.fairness_passed = fairness_res.is_fair
                    db.commit()
        except Exception as dbe:
            logger.warning("Could not update fairness check in DB: %s", str(dbe))
        finally:
            db.close()

        return {"fairness_result": fairness_details}

    @staticmethod
    def human_approval(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 7: Human Approval
        Transition state handler for manual review referrals.
        """
        logger.info("LangGraph Node: Executing Human Approval (check referral status)...")
        reco_res = state.get("recommendation") or {}
        decision = reco_res.get("decision", "REFER")
        applicant_data = state["applicant"]
        app_id = applicant_data.get("application_id")

        human_app = {}
        if decision == "REFER":
            human_app["status"] = "PENDING_REVIEW"
            human_app["reviewer"] = "SYSTEM"
            human_app["comments"] = "Awaiting review due to referral constraints."
        else:
            human_app["status"] = "AUTO_PROCESSED"
            human_app["reviewer"] = "SYSTEM"
            human_app["comments"] = f"Auto-{decision.lower()} processed based on system checks."

        db = SessionLocal()
        try:
            if app_id:
                human_decision_repo.create(db, obj_in={
                    "application_id": app_id,
                    "decision": "REFER" if decision == "REFER" else decision,
                    "comments": human_app.get("comments"),
                    "underwriter_email": "system@techvest.com"
                })
                
                # Update application status
                db_app = application_repo.get(db, app_id)
                if db_app:
                    db_app.status = "PENDING_APPROVAL" if decision == "REFER" else (decision + "ED")
                db.commit()
        except Exception as dbe:
            logger.warning("Could not persist human decision log in DB: %s", str(dbe))
        finally:
            db.close()

        return {"human_approval": human_app}

    @staticmethod
    def audit_logging(state: UnderwritingState) -> Dict[str, Any]:
        """
        Node 8: Audit Logging
        Generates and saves a complete workflow execution trace in the database.
        """
        logger.info("LangGraph Node: Executing Audit Logging...")
        applicant_data = state["applicant"]
        reco_res = state.get("recommendation") or {}

        db = SessionLocal()
        try:
            db_log = audit_log_repo.create(db, obj_in={
                "application_id": applicant_data.get("application_id"),
                "action": "WORKFLOW_EXECUTION",
                "performed_by": "LANGGRAPH_ENGINE",
                "details": {"decision": reco_res.get("decision"), "reasoning": reco_res.get("reasoning")}
            })
            
            audit_details = {
                "log_id": db_log.id,
                "action": "WORKFLOW_EXECUTION",
                "performed_by": "LANGGRAPH_ENGINE",
                "timestamp": str(db_log.timestamp)
            }
            return {"audit_data": audit_details}
        except Exception as dbe:
            logger.error("Audit log database write failed: %s", str(dbe))
            return {"audit_data": {"action": "WORKFLOW_EXECUTION", "status": "LOG_WRITE_FAILED"}}
        finally:
            db.close()
