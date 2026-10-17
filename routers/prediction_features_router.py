import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.prediction_feature_schema import (
    PredictionFeatureCreate,
    PredictionFeatureResponse,
)
from services.prediction_feature_service import PredictionFeatureService

router = APIRouter(prefix="/analytics/features", tags=["Prediction Features"])


@router.post(
    "", response_model=PredictionFeatureResponse, status_code=status.HTTP_201_CREATED
)
def save_feature_snapshot(
    payload: PredictionFeatureCreate, db: Session = Depends(get_db)
):
    service = PredictionFeatureService(db)
    return service.save_snapshot(payload.inference_id, payload.historical_features)


@router.get("/inference/{inference_id}", response_model=PredictionFeatureResponse)
def get_feature_snapshot(inference_id: uuid.UUID, db: Session = Depends(get_db)):
    service = PredictionFeatureService(db)
    return service.fetch_snapshot_by_inference(inference_id)
