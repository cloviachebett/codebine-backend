import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from auth_dependency import require_admin
from database import get_db
from models.users import User
from schemas.model_version_schema import (
    ModelVersionCreate,
    ModelVersionResponse,
    PredictFromRainfallRequest,
    PredictResponse,
)
from services.current_user import get_current_user
from services.model_version_service import ModelVersionService

router = APIRouter(prefix="/analytics/models", tags=["Model Versions Operations"])


@router.post(
    "", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED
)
def create_model_version(
    payload: ModelVersionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    service = ModelVersionService(db)
    return service.register_version(payload.model_dump())


@router.get("/active", response_model=ModelVersionResponse)
def get_active_model_version(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ModelVersionService(db).fetch_active()


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
    admin: User = Depends(require_admin),
):
    return ModelVersionService(db).predict_from_request(model_version_id, payload)
