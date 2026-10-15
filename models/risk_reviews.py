import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from models._enums import ReviewDecision
from models._types import enum_column, utcnow
from database import Base


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

    review_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    inference_id = Column(
        Uuid, ForeignKey("risk_inferences.inference_id"), nullable=True
    )
    alert_id = Column(Uuid, ForeignKey("emergency_alerts.alert_id"), nullable=True)
    reviewed_by = Column(Uuid, ForeignKey("users.user_id"), nullable=False)
    decision = Column(
        enum_column(ReviewDecision, "review_decision_enum"), nullable=False
    )
    comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    inference = relationship("RiskInference", back_populates="risk_reviews")
    alert = relationship("EmergencyAlert", back_populates="risk_reviews")
    reviewed_by_user = relationship("User", back_populates="risk_reviews")
