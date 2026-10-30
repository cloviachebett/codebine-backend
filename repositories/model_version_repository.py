import uuid
from sqlalchemy.orm import Session
from models._enums import ModelStatus
from models.model_versions import ModelVersion


class ModelVersionRepository:
    def __init__(self):
        self.model = ModelVersion

    def create(
        self,
        db: Session,
        model_name: str,
        version_code: str,
        model_type: str,
        model_path: str,
        precision: dict,
        recall: dict,
        f1_score: dict,
        model_status: str,
    ) -> ModelVersion:
        db_obj = self.model(
            model_name=model_name,
            version_code=version_code,
            model_type=model_type,
            model_path=model_path,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            model_status=model_status,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id(
        self, db: Session, model_version_id: uuid.UUID
    ) -> ModelVersion | None:
        return (
            db.query(self.model)
            .filter(self.model.model_version_id == model_version_id)
            .first()
        )

    def get_by_unique_version(
        self, db: Session, model_name: str, version_code: str
    ) -> ModelVersion | None:
        return (
            db.query(self.model)
            .filter(
                self.model.model_name == model_name,
                self.model.version_code == version_code,
            )
            .first()
        )

    def newest_with_status(
        self, db: Session, model_status: ModelStatus
    ) -> ModelVersion | None:
        return (
            db.query(self.model)
            .filter(self.model.model_status == model_status)
            .order_by(self.model.created_at.desc())
            .first()
        )


model_version_repository = ModelVersionRepository()
