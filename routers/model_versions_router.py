import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.model_version_schema import (
    ModelVersionCreate,
    ModelVersionResponse,
    PredictFromRainfallRequest,
    PredictResponse,
)
from services.model_version_service import ModelVersionService

router = APIRouter(prefix="/analytics/models", tags=["Model Versions Operations"])


@router.post(
    "", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED
)
def create_model_version(payload: ModelVersionCreate, db: Session = Depends(get_db)):
    service = ModelVersionService(db)
    return service.register_version(payload.model_dump())


@router.get("/{model_version_id}", response_model=ModelVersionResponse)
def get_model_version(model_version_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ModelVersionService(db)
    return service.fetch_version(model_version_id)


@router.post(
    "/{model_version_id}/predict-from-rainfall",
    response_model=PredictResponse,
    status_code=status.HTTP_201_CREATED,
)
def predict_from_rainfall(
    model_version_id: uuid.UUID,
    payload: PredictFromRainfallRequest,
    db: Session = Depends(get_db),
):
    service = ModelVersionService(db)
    result = service.predict_from_rainfall(
        model_version_id,
        payload.sector_id,
        [obs.model_dump() for obs in payload.rainfall_observations],
    )
    return result
