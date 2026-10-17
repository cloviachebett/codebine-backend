import uuid
from sqlalchemy.orm import Session
from models.prediction_features import PredictionFeature


class PredictionFeatureRepository:
    def __init__(self):
        self.model = PredictionFeature

    def create(
        self, db: Session, inference_id: uuid.UUID, historical_features: dict
    ) -> PredictionFeature:
        db_obj = self.model(
            inference_id=inference_id,
            historical_features=historical_features,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_inference_id(
        self, db: Session, inference_id: uuid.UUID
    ) -> PredictionFeature | None:
        return (
            db.query(self.model).filter(self.model.inference_id == inference_id).first()
        )


prediction_feature_repository = PredictionFeatureRepository()
