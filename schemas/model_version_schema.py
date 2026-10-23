import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, field_validator


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


class RainfallObservation(BaseModel):
    rain_1day_mm: float
    rain_3day_mm: float
    rain_7day_mm: float
    rain_10day_mm: float
    rain_30day_mm: float
    observation_time: str  # ISO format: "2026-09-27T03:00:00+03:00"

    @field_validator(
        "rain_1day_mm", "rain_3day_mm", "rain_7day_mm", "rain_10day_mm", "rain_30day_mm"
    )
    @classmethod
    def validate_rainfall(cls, v):
        if v < 0:
            raise ValueError("Rainfall values must be non-negative")
        return v

    @field_validator("observation_time")
    @classmethod
    def validate_observation_time(cls, v):
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                "observation_time must be ISO format (e.g., 2026-09-27T03:00:00+03:00)"
            )
        return v


class PredictFromRainfallRequest(BaseModel):
    sector_id: uuid.UUID
    rainfall_observations: List[RainfallObservation]


class PredictResponse(BaseModel):
    inference_id: uuid.UUID
    risk_score: float
    risk_level: str
    prediction_time: datetime
    feature_snapshot_id: uuid.UUID

    class Config:
        from_attributes = True
