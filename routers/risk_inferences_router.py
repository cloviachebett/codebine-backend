import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.risk_inference_schema import RiskInferenceCreate, RiskInferenceResponse
from services.risk_inference_service import RiskInferenceService

router = APIRouter(prefix="/analytics/inferences", tags=["Risk Inferences"])


@router.post(
    "", response_model=RiskInferenceResponse, status_code=status.HTTP_201_CREATED
)
def log_inference(payload: RiskInferenceCreate, db: Session = Depends(get_db)):
    service = RiskInferenceService(db)
    result = service.record_prediction(
        model_version_id=payload.model_version_id,
        sector_id=payload.sector_id,
        risk_level=payload.risk_level,
        risk_score=payload.risk_score,
    )
    return result


@router.get("/{inference_id}", response_model=RiskInferenceResponse)
def get_inference(inference_id: uuid.UUID, db: Session = Depends(get_db)):
    service = RiskInferenceService(db)
    result = service.fetch_prediction(inference_id)
    return result
