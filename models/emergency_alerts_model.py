import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import AlertChannel, AlertSeverity, AlertStatus
from models._types import enum_column, utcnow
from database import Base


class EmergencyAlert(Base):
    __tablename__ = "emergency_alert_table"

    alert_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    inference_id = Column(
        Uuid, ForeignKey("risk_inference_table.inference_id"), nullable=False
    )
    sector_id = Column(Uuid, ForeignKey("sector_table.sector_id"), nullable=False)
    alert_message = Column(Text, nullable=False)
    severity = Column(enum_column(AlertSeverity, "alert_severity_enum"), nullable=False)
    channel = Column(enum_column(AlertChannel, "alert_channel_enum"), nullable=False)
    alert_status = Column(
        enum_column(AlertStatus, "alert_status_enum"),
        nullable=False,
        default=AlertStatus.PENDING_REVIEW,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    inference = relationship("RiskInference", back_populates="emergency_alerts")
    sector = relationship("Sector", back_populates="emergency_alerts")
    risk_reviews = relationship(
        "RiskReview", back_populates="alert", cascade="all, delete-orphan"
    )
