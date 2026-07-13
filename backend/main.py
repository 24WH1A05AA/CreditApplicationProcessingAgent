import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.utils.logging import logger

from contextlib import asynccontextmanager
from backend.database.session import Base, engine
from backend.models import db_models  # Import to register models in Base metadata
from backend.rag.pipeline import rag_pipeline

# Set up lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up %s in %s environment", settings.APP_NAME, settings.ENV)
    
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
    # Shutdown
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
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root/Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "version": "1.0.0"
    }

# Mock API routes for each workflow stage (to be replaced with actual routers as they are implemented)
@app.post("/applications", tags=["Applications"])
async def create_application(application_data: dict):
    logger.info("Intake loan application received")
    return {"message": "Application received", "status": "PENDING_DOCS"}

@app.post("/documents/upload", tags=["Documents"])
async def upload_document():
    logger.info("Document upload received")
    return {"message": "Document uploaded successfully"}

@app.post("/applications/score", tags=["Scoring"])
async def score_application():
    logger.info("Credit score and DTI calculation request")
    return {"message": "Scored successfully"}

@app.post("/recommendation", tags=["Recommendations"])
async def recommend():
    logger.info("Decision recommendation generated")
    return {"message": "Recommendation generated"}

@app.post("/fairness/check", tags=["Fairness"])
async def fairness_check():
    logger.info("Identity-blind fairness check executed")
    return {"message": "Fairness check passed"}

from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.schemas import HumanDecisionCreate
from backend.database.repository import human_decision_repo, application_repo, audit_log_repo

@app.post("/approval", tags=["Governance"])
async def record_approval(decision_data: HumanDecisionCreate, db: Session = Depends(get_db)):
    logger.info("Underwriter human decision captured for application %s", decision_data.application_id)
    
    # 1. Fetch application
    application = application_repo.get(db, decision_data.application_id)
    if not application:
        raise HTTPException(
            status_code=404,
            detail=f"Application not found: {decision_data.application_id}"
        )
        
    # 2. Persist decision
    db_decision = human_decision_repo.create(db, obj_in={
        "application_id": decision_data.application_id,
        "decision": decision_data.decision,
        "comments": decision_data.comments,
        "underwriter_email": decision_data.underwriter_email
    })
    
    # 3. Update application status
    # Standard states: APPROVED, DECLINED, REFER
    mapped_status = decision_data.decision.upper()
    if mapped_status in ["APPROVE", "APPROVED"]:
        application.status = "APPROVED"
    elif mapped_status in ["DECLINE", "REJECT", "DECLINED"]:
        application.status = "DECLINED"
    else:
        application.status = "REFER"
        
    db.commit()
    
    # 4. Save audit log
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
    logger.info("Querying audit trail logs for application: %s", application_id)
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

@app.get("/applications/{id}", tags=["Applications"])
async def get_application(id: str):
    logger.info("Query application details for %s", id)
    return {"id": id}

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
