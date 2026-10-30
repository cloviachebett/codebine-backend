import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from auth_dependency import require_admin
from database import get_db
from models.users import User
from schemas.risk_inference_schema import (
    RiskInferenceCreate,
    RiskInferenceListItem,
    RiskInferenceResponse,
)
from services.current_user import get_current_user
from services.risk_inference_service import RiskInferenceService

router = APIRouter(prefix="/analytics/inferences", tags=["Risk Inferences"])


@router.post(
    "", response_model=RiskInferenceResponse, status_code=status.HTTP_201_CREATED
)
def log_inference(
    payload: RiskInferenceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    service = RiskInferenceService(db)
    result = service.record_prediction(
        model_version_id=payload.model_version_id,
        sector_id=payload.sector_id,
        risk_level=payload.risk_level,
        risk_score=payload.risk_score,
    )
    return result


@router.get("", response_model=list[RiskInferenceListItem])
def list_inferences(
    district: str | None = Query(None),
    risk_level: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    latest_only: bool = Query(False),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return RiskInferenceService(db).list_predictions(
        district=district,
        risk_level=risk_level,
        start=start_date,
        end=end_date,
        latest_only=latest_only,
        limit=limit,
    )


@router.get("/{inference_id}", response_model=RiskInferenceResponse)
def get_inference(inference_id: uuid.UUID, db: Session = Depends(get_db)):
    service = RiskInferenceService(db)
    result = service.fetch_prediction(inference_id)
    return result
