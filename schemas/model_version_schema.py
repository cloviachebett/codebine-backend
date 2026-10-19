import uuid
from datetime import datetime
from pydantic import BaseModel


class ModelVersionCreate(BaseModel):
    model_name: str
    version_code: str
    model_type: str
    model_path: str
    precision: dict
    recall: dict
    f1_score: dict
    model_status: str = "READY"


class ModelVersionResponse(BaseModel):
    model_version_id: uuid.UUID
    model_name: str
    version_code: str
    model_type: str
    model_path: str
    precision: dict
    recall: dict
    f1_score: dict
    model_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PredictFromRainfallRequest(BaseModel):
    sector_id: uuid.UUID
    rainfall_observations: list  # [{rain_1day_mm, rain_3day_mm, rain_7day_mm, rain_10day_mm, rain_30day_mm}, ...]
