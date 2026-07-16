import os
import shutil
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.config import settings
from backend.utils.logging import logger
from backend.utils.observability import ObservabilityManager
from backend.database.session import Base, engine, get_db
from backend.models import db_models
from backend.models.schemas import (
    ApplicationCreate,
    HumanDecisionCreate,
    Application as ApplicationSchema,
    Document as DocumentSchema,
    Recommendation as RecommendationSchema,
    UserCreate,
    UserResponse,
    Token
)
from backend.database.repository import (
    applicant_repo,
    application_repo,
    document_repo,
    policy_result_repo,
    recommendation_repo,
    human_decision_repo,
    audit_log_repo,
    user_repo
)
from backend.rag.pipeline import rag_pipeline
from backend.agents.workflow import run_underwriting_workflow
from backend.utils.auth import RoleChecker, get_password_hash, verify_password, create_access_token
from backend.utils.evaluation_queries import get_evaluation_dashboard_data

# Configure document uploads folder
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up %s in %s environment", settings.APP_NAME, settings.ENV)
    
    # Ensure uploads dir exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Initialize Database Tables
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # Auto-seed mock data if database is empty
        from backend.database.session import SessionLocal
        from backend.models.db_models import Application
        db_session = SessionLocal()
        try:
            if db_session.query(Application).count() == 0:
                logger.info("No applications found in database. Seeding mock data...")
                from scripts.populate_demo_data import populate_mock_data
                populate_mock_data()
                logger.info("Mock data seeded successfully.")
        except Exception as seed_err:
            logger.error("Failed to seed database: %s", str(seed_err))
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error("Error creating database tables: %s", str(e))
        
    # Initialize RAG Pipeline
    logger.info("Initializing RAG Pipeline...")
    try:
        rag_pipeline.initialize_pipeline()
        logger.info("RAG Pipeline initialized successfully.")
    except Exception as e:
        logger.error("Error initializing RAG Pipeline: %s", str(e))
        
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic AI Loan/Credit Application Processing Decision Support System",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= Global Exception Handlers =================

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    logger.error("Database Error encountered: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "DATABASE_ERROR",
            "message": "A database persistence error occurred while processing this request.",
            "detail": str(exc)
        }
    )

@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(request, exc):
    logger.error("File Not Found: %s", str(exc))
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "error_type": "FILE_NOT_FOUND",
            "message": "The requested file or document could not be located on disk.",
            "detail": str(exc)
        }
    )

@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    logger.error("Value Error encountered: %s", str(exc))
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "error_type": "VALIDATION_ERROR",
            "message": "An invalid parameter or data validation error occurred.",
            "detail": str(exc)
        }
    )


# ================= System Endpoints =================

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "version": "1.0.0"
    }


@app.post("/database/seed", tags=["System"])
async def seed_database():
    """
    Manually triggers database seeding with demo data.
    """
    logger.info("REST: Manual database seed requested")
    try:
        from scripts.populate_demo_data import populate_mock_data
        populate_mock_data()
        return {"status": "success", "message": "Demo data seeded successfully"}
    except Exception as e:
        logger.error("Failed manual database seed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to seed database: {str(e)}")


# ================= Authentication Endpoints =================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new system user with Role-based access control.
    """
    logger.info("Registering new user: %s with role: %s", user_in.username, user_in.role)
    existing_user = user_repo.get_by_username(db, username=user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    db_user = user_repo.create(db, obj_in={
        "username": user_in.username,
        "hashed_password": hashed_pwd,
        "role": user_in.role.upper()
    })
    return db_user

@app.post("/auth/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Validates user credentials and returns a signed JWT access token.
    """
    logger.info("Authenticating login request for user: %s", form_data.username)
    user = user_repo.get_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


# ================= Application REST Endpoints =================

@app.post("/applications", response_model=dict, tags=["Applications"])
async def create_loan_application(
    app_in: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER"]))
):
    """
    1. Upload Application details and registers applicant in database.
    """
    logger.info("REST: Creating loan application for applicant %s", app_in.applicant.email)
    
    # Run Input Guardrails
    from backend.utils.guardrails import GuardrailEngine
    guardrail_errors = GuardrailEngine.validate_inputs(app_in.model_dump())
    if guardrail_errors:
        logger.warning("REST: Blocked loan application due to guardrail violations: %s", "; ".join(guardrail_errors))
        raise HTTPException(
            status_code=400,
            detail="; ".join(guardrail_errors)
        )
        
    # Fetch or Create Applicant
    db_applicant = applicant_repo.get_by_email(db, app_in.applicant.email)
    if not db_applicant:
        db_applicant = applicant_repo.create(db, obj_in=app_in.applicant.model_dump())
        
    # Create Loan Application
    db_app = application_repo.create(db, obj_in={
        "applicant_id": db_applicant.id,
        "loan_amount": app_in.loan_amount,
        "loan_purpose": app_in.loan_purpose,
        "status": "INTAKE"
    })
    
    # Audit log
    audit_log_repo.create(db, obj_in={
        "application_id": db_app.id,
        "action": "CREATE_APPLICATION",
        "performed_by": "SYSTEM",
        "details": {"applicant_id": db_applicant.id, "loan_amount": app_in.loan_amount}
    })
    
    return {
        "status": "success",
        "message": "Application uploaded successfully.",
        "application_id": db_app.id,
        "applicant_id": db_applicant.id,
        "application_status": db_app.status
    }


@app.post("/applications/{application_id}/documents", tags=["Documents"])
async def upload_loan_documents(
    application_id: str,
    document_type: str = Form(..., description="PAN, Aadhaar, Salary Slip, Bank Statement"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER"]))
):
    """
    2. Upload Documents associated with application.
    """
    logger.info("REST: Uploading document type %s for application %s", document_type, application_id)
    
    application = application_repo.get(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
        
    # Save file locally
    file_ext = os.path.splitext(file.filename)[1]
    safe_name = f"{application_id}_{document_type.replace(' ', '_').lower()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document on disk: {str(e)}")
        
    # Create database document row
    db_doc = document_repo.create(db, obj_in={
        "application_id": application_id,
        "document_type": document_type,
        "file_path": file_path,
        "is_valid": None,
        "validation_result": None
    })
    
    # Update application status
    application.status = "DOCS_UPLOADED"
    db.commit()
    
    audit_log_repo.create(db, obj_in={
        "application_id": application_id,
        "action": "UPLOAD_DOCUMENT",
        "performed_by": "SYSTEM",
        "details": {"document_type": document_type, "file_path": file_path}
    })
    
    return {
        "status": "success",
        "message": f"Document '{document_type}' uploaded successfully.",
        "document_id": db_doc.id,
        "file_path": file_path
    }


@app.post("/applications/{application_id}/process", tags=["Processing"])
async def process_loan_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER"]))
):
    """
    3. Process Application - runs the compiled LangGraph workflow end-to-end.
    """
    logger.info("REST: Triggering LangGraph workflow processing for application %s", application_id)
    
    application = application_repo.get(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
        
    db_applicant = applicant_repo.get(db, application.applicant_id)
    db_docs = document_repo.get_by_application(db, application_id)
    
    # Prepare initial state for LangGraph
    initial_state = {
        "applicant": {
            "id": db_applicant.id,
            "application_id": application_id,
            "first_name": db_applicant.first_name,
            "last_name": db_applicant.last_name,
            "email": db_applicant.email,
            "dob": db_applicant.dob,
            "monthly_income": db_applicant.monthly_income,
            "existing_emi": db_applicant.existing_emi,
            "loan_amount": application.loan_amount,
            "loan_purpose": application.loan_purpose
        },
        "documents": [
            {
                "document_type": doc.document_type,
                "file_path": doc.file_path
            } for doc in db_docs
        ],
        "validation_result": None,
        "retrieved_policy": None,
        "score": None,
        "recommendation": None,
        "fairness_result": None,
        "audit_data": None,
        "human_approval": None,
        "metadata": {}
    }
    
    # Invoke LangGraph Graph
    final_state = run_underwriting_workflow(initial_state)
    
    if final_state.get("metadata", {}).get("workflow_status") == "FAILED":
        raise HTTPException(
            status_code=500,
            detail=f"Underwriting workflow crashed: {final_state['metadata'].get('workflow_execution_error')}"
        )
        
    return {
        "status": "success",
        "message": "Loan application processed successfully.",
        "scoring": final_state.get("score"),
        "recommendation": final_state.get("recommendation"),
        "fairness": final_state.get("fairness_result")
    }


@app.get("/applications/{application_id}/recommendation", response_model=dict, tags=["Recommendations"])
async def get_application_recommendation(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    4. Recommendation details retrieval.
    """
    logger.info("REST: Querying recommendation details for application: %s", application_id)
    reco = recommendation_repo.get_by_application(db, application_id)
    if not reco:
        raise HTTPException(status_code=404, detail="Recommendation not found. Process the application first.")
        
    return {
        "application_id": application_id,
        "decision": reco.decision,
        "reasoning": reco.reasoning,
        "composite_score": reco.composite_score,
        "fairness_passed": reco.fairness_passed,
        "created_at": str(reco.created_at)
    }


@app.get("/applications/{application_id}/observability", tags=["Observability"])
async def get_application_observability(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    Retrieves execution traces, timings, token usage, and a Mermaid chart for the agent's workflow.
    """
    logger.info("REST: Fetching observability metrics for application %s", application_id)
    
    # Query database for WORKFLOW_EXECUTION audit log
    logs = audit_log_repo.get_by_application(db, application_id)
    wf_log = next((log for log in logs if log.action == "WORKFLOW_EXECUTION"), None)
    
    if not wf_log:
        raise HTTPException(
            status_code=404,
            detail=f"Observability metrics not found for application {application_id}. Run analysis first."
        )
        
    details = wf_log.details or {}
    meta = details.get("metadata", {})
    execution_path = meta.get("execution_path", [])
    
    # Generate flowchart
    mermaid_graph = ObservabilityManager.generate_mermaid_flowchart(execution_path)
    
    return {
        "application_id": application_id,
        "execution_path": execution_path,
        "node_timings_ms": meta.get("node_timings", {}),
        "total_latency_ms": sum(meta.get("node_timings", {}).values()),
        "token_usage": meta.get("token_usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}),
        "mermaid_chart": mermaid_graph
    }


@app.post("/approval", tags=["Governance"])
async def record_approval(
    decision_data: HumanDecisionCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER"]))
):
    """
    5. Human Approval governance submission.
    """
    logger.info("REST: Underwriter human decision captured for application %s", decision_data.application_id)
    
    application = application_repo.get(db, decision_data.application_id)
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {decision_data.application_id}")
        
    db_decision = human_decision_repo.create(db, obj_in={
        "application_id": decision_data.application_id,
        "decision": decision_data.decision,
        "comments": decision_data.comments,
        "underwriter_email": decision_data.underwriter_email
    })
    
    # Map decision states: APPROVED, DECLINED, REFER
    mapped_status = decision_data.decision.upper()
    if mapped_status in ["APPROVE", "APPROVED"]:
        application.status = "APPROVED"
    elif mapped_status in ["DECLINE", "REJECT", "DECLINED"]:
        application.status = "DECLINED"
    else:
        application.status = "REFER"
        
    db.commit()
    
    audit_log_repo.create(db, obj_in={
        "application_id": decision_data.application_id,
        "action": "HUMAN_APPROVAL",
        "performed_by": decision_data.underwriter_email,
        "details": {"decision": decision_data.decision, "comments": decision_data.comments}
    })
    
    return {
        "status": "success",
        "message": f"Human decision '{decision_data.decision}' persisted successfully.",
        "decision_id": db_decision.id,
        "application_status": application.status
    }


@app.get("/audit/{application_id}", tags=["Audit"])
async def get_audit(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "AUDITOR"]))
):
    """
    6. Audit History session tracking.
    """
    logger.info("REST: Querying audit trail logs for application: %s", application_id)
    logs = audit_log_repo.get_by_application(db, application_id)
    return {
        "application_id": application_id,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "performed_by": log.performed_by,
                "details": log.details,
                "timestamp": str(log.timestamp)
            } for log in logs
        ]
    }


@app.get("/evaluation/dashboard-data", tags=["Evaluation"])
async def get_dashboard_evaluation_data(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    Retrieves aggregated and detailed evaluations of all applications processed by the AI agent.
    """
    logger.info("REST: Querying evaluation dashboard data")
    return get_evaluation_dashboard_data(db)


@app.get("/applications", response_model=List[dict], tags=["Applications"])
async def list_loan_applications(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    List all loan applications in the system.
    """
    logger.info("REST: Fetching all loan applications")
    apps = db.query(db_models.Application).order_by(db_models.Application.created_at.desc()).limit(100).all()
    result = []
    for app in apps:
        db_applicant = applicant_repo.get(db, app.applicant_id)
        result.append({
            "id": app.id,
            "loan_amount": app.loan_amount,
            "loan_purpose": app.loan_purpose,
            "status": app.status,
            "credit_score": app.credit_score,
            "dti_ratio": app.dti_ratio,
            "created_at": str(app.created_at),
            "updated_at": str(app.updated_at),
            "applicant": {
                "first_name": db_applicant.first_name if db_applicant else "",
                "last_name": db_applicant.last_name if db_applicant else "",
                "email": db_applicant.email if db_applicant else "",
                "monthly_income": db_applicant.monthly_income if db_applicant else 0.0,
                "existing_emi": db_applicant.existing_emi if db_applicant else 0.0
            }
        })
    return result


@app.get("/applications/{application_id}", response_model=dict, tags=["Applications"])
async def get_application_status(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    7. Application Status metadata query.
    """
    logger.info("REST: Fetching status details for application %s", application_id)
    application = application_repo.get(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
        
    db_applicant = applicant_repo.get(db, application.applicant_id)
    db_docs = document_repo.get_by_application(db, application_id)
    
    from backend.tools.credit_engine import CreditScoringEngine
    bureau_res = CreditScoringEngine.fetch_credit_bureau_score(db_applicant.email)
    
    return {
        "id": application.id,
        "bureau_details": {
            "credit_score": bureau_res.credit_score,
            "has_active_defaults": bureau_res.has_active_defaults,
            "inquiries_last_6m": bureau_res.inquiries_last_6m,
            "historical_scores": bureau_res.historical_scores,
            "payment_history_pct": bureau_res.payment_history_pct,
            "credit_mix": bureau_res.credit_mix,
            "credit_age_years": bureau_res.credit_age_years
        },
        "applicant": {
            "first_name": db_applicant.first_name,
            "last_name": db_applicant.last_name,
            "email": db_applicant.email,
            "dob": db_applicant.dob,
            "monthly_income": db_applicant.monthly_income,
            "existing_emi": db_applicant.existing_emi
        },
        "loan_amount": application.loan_amount,
        "loan_purpose": application.loan_purpose,
        "status": application.status,
        "credit_score": application.credit_score,
        "dti_ratio": application.dti_ratio,
        "created_at": str(application.created_at),
        "updated_at": str(application.updated_at),
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "file_path": doc.file_path,
                "is_valid": doc.is_valid
            } for doc in db_docs
        ]
    }


class PolicyChatRequest(BaseModel):
    query: str

@app.post("/rag/chat", tags=["Policy RAG"])
async def policy_chat_endpoint(
    request: PolicyChatRequest,
    current_user: db_models.User = Depends(RoleChecker(["ADMIN", "UNDERWRITER", "AUDITOR"]))
):
    """
    RAG Policy Chatbot endpoint that retrieves policy guidelines and answers questions.
    """
    query = request.query
    logger.info("REST: RAG Policy Chatbot query: '%s'", query)
    
    # Retrieve clauses
    from backend.rag.pipeline import rag_pipeline
    clauses = rag_pipeline.retrieve(query, k=3)
    
    # Prepare system message context
    context = "\n\n".join([f"Source: {c['citation']}\n{c['content']}" for c in clauses])
    
    is_mock_key = (
        not settings.OPENAI_API_KEY 
        or settings.OPENAI_API_KEY == "mock-key-for-development"
        or not settings.OPENAI_API_KEY.startswith("sk-")
    )
    
    if is_mock_key:
        if "dti" in query.lower():
            answer = "According to our Credit Underwriting Policy (Clause CP-DTI-01), the maximum allowed Debt-to-Income (DTI) ratio is 45%. Candidates with a DTI ratio between 40% and 45% are referred for manual underwriter review."
        elif "credit" in query.lower() or "score" in query.lower():
            answer = "Under our Credit Score Threshold Guidelines (Clause CP-CS-01), a credit score of 750 or higher is required for auto-approval. Scores between 650 and 749 are referred for manual review, and scores below 650 are auto-declined. Active write-offs or defaults (Clause CP-CS-02) result in automatic decline."
        elif "income" in query.lower():
            answer = "Under our Income Stability Guidelines (Clause CP-INC-01), the minimum monthly income requirement is INR 25,000 for salaried applicants and INR 35,000 for self-employed applicants. Applicants below these limits are declined."
        elif "kyc" in query.lower():
            answer = "According to RBI KYC Guidelines (Clause RBI-KYC-01), the accepted Officially Valid Documents (OVD) for identity and address verification include PAN, Aadhaar, Passport, Voter ID, and Driver's License."
        else:
            answer = f"Based on the retrieved policy context:\n\n{context}\n\nPlease contact risk compliance if you require special policy exceptions."
    else:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        try:
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
                temperature=0.3
            )
            prompt = (
                "You are an expert Credit Policy compliance officer assisting an underwriter.\n"
                "Answer the user query based ONLY on the retrieved credit policies context below. "
                "If the context does not contain sufficient information, state that clearly.\n\n"
                f"RETRIEVED POLICY CONTEXT:\n{context}\n\n"
                f"USER QUERY: {query}\n"
                "Format your answer professionally in markdown. Cite the Clause codes (e.g. CP-CS-01) where relevant."
            )
            messages = [
                SystemMessage(content="You are a credit compliance assistant."),
                HumanMessage(content=prompt)
            ]
            response = llm.invoke(messages)
            answer = response.content.strip()
        except Exception as e:
            answer = f"Error processing query via LLM: {str(e)}. Fallback context retrieved:\n\n{context}"
            
    return {
        "query": query,
        "answer": answer,
        "citations": [c["citation"] for c in clauses]
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

