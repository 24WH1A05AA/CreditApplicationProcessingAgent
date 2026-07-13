import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.utils.logging import logger

from contextlib import asynccontextmanager
from backend.database.session import Base, engine
from backend.models import db_models  # Import to register models in Base metadata

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

@app.post("/approval", tags=["Governance"])
async def record_approval():
    logger.info("Underwriter human decision captured")
    return {"message": "Human decision recorded"}

@app.get("/audit/{id}", tags=["Audit"])
async def get_audit(id: str):
    logger.info("Audit log query for application %s", id)
    return {"id": id, "logs": []}

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
