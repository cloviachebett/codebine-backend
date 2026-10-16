import uuid
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from repositories.risk_inference_repository import risk_inference_repository
from models.model_versions import ModelVersion
from models.sectors import Sector


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
        sector = self.db.get(Sector, sector_id)
        if not sector:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sector not found.",
            )

        if model_version_id is not None:
            model_version = self.db.get(ModelVersion, model_version_id)
            if not model_version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Model version not found.",
                )

        try:
            return self.repo.create(
                self.db, model_version_id, sector_id, risk_level, risk_score
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not record prediction. Referenced records may be missing.",
            )

    def fetch_prediction(self, inference_id: uuid.UUID):
        result = self.repo.get_by_id(self.db, inference_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction signature log entries not found.",
            )
        return result
