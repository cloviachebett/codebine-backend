from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)

from models._enums import ReviewDecision

Comments = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inference_id: UUID | None = None
    alert_id: UUID | None = None
    decision: ReviewDecision
    comments: Comments | None = None

    @model_validator(mode="after")
    def exactly_one_target(self):
        if (self.inference_id is None) == (self.alert_id is None):
            raise ValueError("Provide exactly one of inference_id or alert_id")
        return self


class ReviewRead(BaseModel):
    review_id: UUID
    inference_id: UUID | None
    alert_id: UUID | None
    decision: ReviewDecision
    comments: str | None
    reviewed_by: UUID
    reviewer_name: str
    reviewed_at: datetime

    @field_validator("reviewed_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
