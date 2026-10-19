import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionFeatureCreate(BaseModel):
    inference_id: uuid.UUID
    historical_features: dict


class PredictionFeatureResponse(BaseModel):
    feature_snapshot_id: uuid.UUID
    inference_id: uuid.UUID
    historical_features: dict
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
