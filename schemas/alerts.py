from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from models._enums import AlertSeverity, AlertStatus, RiskLevel


class AlertCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inference_id: UUID


class AlertRead(BaseModel):
    alert_id: UUID
    inference_id: UUID
    sector_id: UUID
    district_name: str
    sector_name: str
    risk_level: RiskLevel
    risk_score: Decimal
    severity: AlertSeverity
    alert_message: str
    alert_status: AlertStatus
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
