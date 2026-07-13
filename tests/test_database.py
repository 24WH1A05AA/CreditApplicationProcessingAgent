import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.session import Base
from backend.models.db_models import Applicant, Application, Document, PolicyResult, Recommendation, AuditLog, HumanDecision

# Setup testing in-memory SQLite engine and session
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create the tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_create_applicant_and_application(db_session):
    # 1. Create Applicant
    new_applicant = Applicant(
        first_name="Jane",
        last_name="Doe",
        dob="1990-05-15",
        email="jane.doe@example.com",
        monthly_income=75000.0,
        existing_emi=5000.0
    )
    db_session.add(new_applicant)
    db_session.commit()
    db_session.refresh(new_applicant)

    assert new_applicant.id is not None
    assert new_applicant.first_name == "Jane"
    assert new_applicant.last_name == "Doe"

    # 2. Create Application linked to Applicant
    new_application = Application(
        applicant_id=new_applicant.id,
        loan_amount=500000.0,
        loan_purpose="Home Improvement",
        status="INTAKE"
    )
    db_session.add(new_application)
    db_session.commit()
    db_session.refresh(new_application)

    assert new_application.id is not None
    assert new_application.applicant_id == new_applicant.id

    # 3. Verify relationships
    queried_applicant = db_session.query(Applicant).filter(Applicant.id == new_applicant.id).first()
    assert len(queried_applicant.applications) == 1
    assert queried_applicant.applications[0].loan_amount == 500000.0

def test_cascade_delete(db_session):
    # Setup applicant and application
    applicant = Applicant(
        first_name="John",
        last_name="Smith",
        dob="1985-10-20",
        email="john.smith@example.com",
        monthly_income=90000.0
    )
    db_session.add(applicant)
    db_session.commit()

    application = Application(
        applicant_id=applicant.id,
        loan_amount=200000.0,
        loan_purpose="Car Loan"
    )
    db_session.add(application)
    db_session.commit()

    # Verify presence
    assert db_session.query(Applicant).count() == 1
    assert db_session.query(Application).count() == 1

    # Delete applicant and check cascade deletes application
    db_session.delete(applicant)
    db_session.commit()

    assert db_session.query(Applicant).count() == 0
    assert db_session.query(Application).count() == 0
