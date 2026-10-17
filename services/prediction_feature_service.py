import uuid
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from repositories.prediction_feature_repository import prediction_feature_repository
from models.risk_inferences import RiskInference


class PredictionFeatureService:
    def __init__(self, db: Session):
        self.repo = prediction_feature_repository
        self.db = db

    def save_snapshot(self, inference_id: uuid.UUID, historical_features: dict):
        # All validation and HTTP exceptions live safely here
        existing = self.repo.get_by_inference_id(self.db, inference_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A prediction feature snapshot matrix already exists for this unique inference ID mapping.",
            )

        inference = self.db.get(RiskInference, inference_id)
        if not inference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inference not found.",
            )

        try:
            return self.repo.create(self.db, inference_id, historical_features)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A prediction feature snapshot matrix already exists for this unique inference ID mapping.",
            )

    def fetch_snapshot_by_inference(self, inference_id: uuid.UUID):
        snapshot = self.repo.get_by_inference_id(self.db, inference_id)
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No historical feature matrix snapshot logs found matching this reference inference record.",
            )
        return snapshot
