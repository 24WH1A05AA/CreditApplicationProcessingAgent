import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.session import Base
from backend.database.repository import (
    applicant_repo,
    application_repo,
    document_repo,
    recommendation_repo,
    human_decision_repo,
    audit_log_repo
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_applicant_repository(db_session):
    # Test Create
    applicant_data = {
        "first_name": "Bob",
        "last_name": "Miller",
        "dob": "1988-12-01",
        "email": "bob.miller@example.com",
        "monthly_income": 80000.0,
        "existing_emi": 4000.0
    }
    new_applicant = applicant_repo.create(db_session, obj_in=applicant_data)
    assert new_applicant.id is not None
    assert new_applicant.first_name == "Bob"

    # Test Get by ID
    fetched_by_id = applicant_repo.get(db_session, new_applicant.id)
    assert fetched_by_id is not None
    assert fetched_by_id.email == "bob.miller@example.com"

    # Test Get by Email
    fetched_by_email = applicant_repo.get_by_email(db_session, "bob.miller@example.com")
    assert fetched_by_email is not None
    assert fetched_by_email.id == new_applicant.id

    # Test Update
    updated = applicant_repo.update(db_session, db_obj=new_applicant, obj_in={"monthly_income": 95000.0})
    assert updated.monthly_income == 95000.0


def test_application_repository(db_session):
    # Setup applicant
    applicant_data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "dob": "1992-03-14",
        "email": "alice.smith@example.com",
        "monthly_income": 120000.0
    }
    applicant = applicant_repo.create(db_session, obj_in=applicant_data)

    # Test Create Application
    app_data = {
        "applicant_id": applicant.id,
        "loan_amount": 1000000.0,
        "loan_purpose": "Education Loan",
        "status": "INTAKE"
    }
    application = application_repo.create(db_session, obj_in=app_data)
    assert application.id is not None
    assert application.status == "INTAKE"

    # Test Get by Applicant
    apps = application_repo.get_by_applicant(db_session, applicant.id)
    assert len(apps) == 1
    assert apps[0].loan_amount == 1000000.0

    # Test Get with Status
    intake_apps = application_repo.get_with_status(db_session, "INTAKE")
    assert len(intake_apps) == 1
