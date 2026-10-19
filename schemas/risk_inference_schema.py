import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiskInferenceCreate(BaseModel):
    sector_id: uuid.UUID
    model_version_id: uuid.UUID | None = None
    risk_level: str
    risk_score: float


class RiskInferenceResponse(BaseModel):
    inference_id: uuid.UUID
    sector_id: uuid.UUID
    model_version_id: uuid.UUID | None
    prediction_time: datetime
    risk_level: str
    risk_score: float

    model_config = ConfigDict(from_attributes=True)
