import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.prediction_feature_schema import (
    PredictionFeatureCreate,
    PredictionFeatureResponse,
)
from repositories.prediction_feature_repository import prediction_feature_repository

router = APIRouter(prefix="/analytics/features", tags=["Prediction Features"])


@router.post(
    "", response_model=PredictionFeatureResponse, status_code=status.HTTP_201_CREATED
)
def save_feature_snapshot(
    payload: PredictionFeatureCreate, db: Session = Depends(get_db)
):
    existing = prediction_feature_repository.get_by_inference_id(
        db, payload.inference_id
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A prediction feature snapshot already exists for this inference ID.",
        )

    return prediction_feature_repository.create(
        db, payload.inference_id, payload.historical_features
    )


@router.get("/inference/{inference_id}", response_model=PredictionFeatureResponse)
def get_feature_snapshot(inference_id: uuid.UUID, db: Session = Depends(get_db)):
    result = prediction_feature_repository.get_by_inference_id(db, inference_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No historical feature matrix snapshot found for this inference record.",
        )
    return result
