from typing import Generic, TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from backend.database.session import Base
from backend.models.db_models import (
    Applicant,
    Application,
    Document,
    PolicyResult,
    Recommendation,
    HumanDecision,
    AuditLog
)

# Define Type Variables for Generic Repository
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    Base Repository class providing standard CRUD operations.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: Dict[str, Any]
    ) -> ModelType:
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


class ApplicantRepository(BaseRepository[Applicant]):
    def __init__(self):
        super().__init__(Applicant)

    def get_by_email(self, db: Session, email: str) -> Optional[Applicant]:
        return db.query(self.model).filter(self.model.email == email).first()


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self):
        super().__init__(Application)

    def get_by_applicant(self, db: Session, applicant_id: str) -> List[Application]:
        return db.query(self.model).filter(self.model.applicant_id == applicant_id).all()

    def get_with_status(self, db: Session, status: str) -> List[Application]:
        return db.query(self.model).filter(self.model.status == status).all()


class DocumentRepository(BaseRepository[Document]):
    def __init__(self):
        super().__init__(Document)

    def get_by_application(self, db: Session, application_id: str) -> List[Document]:
        return db.query(self.model).filter(self.model.application_id == application_id).all()


class PolicyResultRepository(BaseRepository[PolicyResult]):
    def __init__(self):
        super().__init__(PolicyResult)

    def get_by_application(self, db: Session, application_id: str) -> List[PolicyResult]:
        return db.query(self.model).filter(self.model.application_id == application_id).all()


class RecommendationRepository(BaseRepository[Recommendation]):
    def __init__(self):
        super().__init__(Recommendation)

    def get_by_application(self, db: Session, application_id: str) -> Optional[Recommendation]:
        return db.query(self.model).filter(self.model.application_id == application_id).first()


class HumanDecisionRepository(BaseRepository[HumanDecision]):
    def __init__(self):
        super().__init__(HumanDecision)

    def get_by_application(self, db: Session, application_id: str) -> List[HumanDecision]:
        return db.query(self.model).filter(self.model.application_id == application_id).all()


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self):
        super().__init__(AuditLog)

    def get_by_application(self, db: Session, application_id: str) -> List[AuditLog]:
        return db.query(self.model).filter(self.model.application_id == application_id).all()


# Global Singleton Instantiations
applicant_repo = ApplicantRepository()
application_repo = ApplicationRepository()
document_repo = DocumentRepository()
policy_result_repo = PolicyResultRepository()
recommendation_repo = RecommendationRepository()
human_decision_repo = HumanDecisionRepository()
audit_log_repo = AuditLogRepository()
