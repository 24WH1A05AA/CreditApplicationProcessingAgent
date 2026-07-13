import os
import shutil
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.config import settings
from backend.utils.logging import logger
from backend.database.session import Base, engine, get_db
from backend.models import db_models
from backend.models.schemas import (
    ApplicationCreate,
    HumanDecisionCreate,
    Application as ApplicationSchema,
    Document as DocumentSchema,
    Recommendation as RecommendationSchema
)
from backend.database.repository import (
    applicant_repo,
    application_repo,
    document_repo,
    policy_result_repo,
    recommendation_repo,
    human_decision_repo,
    audit_log_repo
)
from backend.rag.pipeline import rag_pipeline
from backend.agents.workflow import run_underwriting_workflow

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


# ================= System Endpoints =================

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "version": "1.0.0"
    }


# ================= Application REST Endpoints =================

@app.post("/applications", response_model=dict, tags=["Applications"])
async def create_loan_application(app_in: ApplicationCreate, db: Session = Depends(get_db)):
    """
    1. Upload Application details and registers applicant in database.
    """
    logger.info("REST: Creating loan application for applicant %s", app_in.applicant.email)
    
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
    db: Session = Depends(get_db)
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
async def process_loan_application(application_id: str, db: Session = Depends(get_db)):
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
async def get_application_recommendation(application_id: str, db: Session = Depends(get_db)):
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


@app.post("/approval", tags=["Governance"])
async def record_approval(decision_data: HumanDecisionCreate, db: Session = Depends(get_db)):
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
async def get_audit(application_id: str, db: Session = Depends(get_db)):
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


@app.get("/applications/{application_id}", response_model=dict, tags=["Applications"])
async def get_application_status(application_id: str, db: Session = Depends(get_db)):
    """
    7. Application Status metadata query.
    """
    logger.info("REST: Fetching status details for application %s", application_id)
    application = application_repo.get(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
        
    db_applicant = applicant_repo.get(db, application.applicant_id)
    db_docs = document_repo.get_by_application(db, application_id)
    
    return {
        "id": application.id,
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


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

