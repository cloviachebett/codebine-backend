import uuid
from sqlalchemy.orm import Session
from models.risk_inferences import RiskInference


class RiskInferenceRepository:
    def __init__(self):
        self.model = RiskInference

    def create(
        self,
        db: Session,
        model_version_id: uuid.UUID | None,
        sector_id: uuid.UUID,
        risk_level: str,
        risk_score: float,
    ) -> RiskInference:
        db_obj = self.model(
            model_version_id=model_version_id,
            sector_id=sector_id,
            risk_level=risk_level,
            risk_score=risk_score,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id(self, db: Session, inference_id: uuid.UUID) -> RiskInference | None:
        return (
            db.query(self.model).filter(self.model.inference_id == inference_id).first()
        )


risk_inference_repository = RiskInferenceRepository()
