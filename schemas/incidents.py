from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
)

Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sector_id: UUID
    event_date: AwareDatetime
    description: Description

    @field_validator("event_date")
    @classmethod
    def event_date_not_in_future(cls, value: datetime) -> datetime:
        if value > datetime.now(timezone.utc):
            raise ValueError("event_date cannot be in the future")
        return value


class IncidentRead(BaseModel):
    report_id: UUID
    sector_id: UUID
    district_name: str
    sector_name: str
    reported_by: UUID | None
    reporter_name: str | None
    reported_at: datetime
    event_date: datetime
    description: str

    @field_validator("reported_at", "event_date")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
