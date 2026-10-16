import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from repositories.risk_inference_repository import risk_inference_repository


class RiskInferenceService:
    def __init__(self, db: Session):
        self.repo = risk_inference_repository
        self.db = db

    def record_prediction(
        self,
        model_version_id: uuid.UUID | None,
        sector_id: uuid.UUID,
        risk_level: str,
        risk_score: float,
    ):
        return self.repo.create(
            self.db, model_version_id, sector_id, risk_level, risk_score
        )

    def fetch_prediction(self, inference_id: uuid.UUID):
        result = self.repo.get_by_id(self.db, inference_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Prediction signature log entries not found.",
            )
        return result
