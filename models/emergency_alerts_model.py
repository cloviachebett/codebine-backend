import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import AlertChannel, AlertSeverity, AlertStatus
from models._types import enum_column, utcnow

if TYPE_CHECKING:
    from models.risk_inferences_model import RiskInference
    from models.risk_reviews_model import RiskReview
    from models.sectors_model import Sector


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    inference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("risk_inferences.inference_id"), nullable=False
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sectors.sector_id"), nullable=False
    )
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        enum_column(AlertSeverity, "alert_severity_enum"), nullable=False
    )
    channel: Mapped[AlertChannel] = mapped_column(
        enum_column(AlertChannel, "alert_channel_enum"), nullable=False
    )
    alert_status: Mapped[AlertStatus] = mapped_column(
        enum_column(AlertStatus, "alert_status_enum"),
        nullable=False,
        default=AlertStatus.PENDING_REVIEW,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    inference: Mapped["RiskInference"] = relationship(back_populates="emergency_alerts")
    sector: Mapped["Sector"] = relationship(back_populates="emergency_alerts")
    risk_reviews: Mapped[list["RiskReview"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EmergencyAlert {self.alert_id} {self.severity}>"
