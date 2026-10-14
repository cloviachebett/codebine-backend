import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import ReviewDecision
from models._types import enum_column, utcnow

if TYPE_CHECKING:
    from models.emergency_alerts_model import EmergencyAlert
    from models.risk_inferences_model import RiskInference
    from models.users_model import User


class RiskReview(Base):
    __tablename__ = "risk_reviews"
    __table_args__ = (
        UniqueConstraint(
            "inference_id", "alert_id", name="uq_risk_reviews_inference_alert"
        ),
        CheckConstraint(
            "(inference_id IS NOT NULL AND alert_id IS NULL) "
            "OR (inference_id IS NULL AND alert_id IS NOT NULL)",
            name="ck_risk_reviews_single_target",
        ),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    inference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("risk_inferences.inference_id"), nullable=True
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("emergency_alerts.alert_id"), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id"), nullable=False
    )
    decision: Mapped[ReviewDecision] = mapped_column(
        enum_column(ReviewDecision, "review_decision_enum"), nullable=False
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    inference: Mapped["RiskInference | None"] = relationship(
        back_populates="risk_reviews"
    )
    alert: Mapped["EmergencyAlert | None"] = relationship(back_populates="risk_reviews")
    reviewed_by_user: Mapped["User"] = relationship(back_populates="risk_reviews")

    def __repr__(self) -> str:
        return f"<RiskReview {self.review_id} {self.decision.value}>"
