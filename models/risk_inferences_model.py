"""ORM model for machine-learning risk inference results per sector."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import RiskLevel
from models._types import enum_column, utcnow

if TYPE_CHECKING:
    from models.emergency_alerts_model import EmergencyAlert
    from models.model_versions_model import ModelVersion
    from models.prediction_features_model import PredictionFeature
    from models.risk_reviews_model import RiskReview
    from models.sectors_model import Sector


class RiskInference(Base):
    """A risk classification produced for one sector at one moment in time."""

    __tablename__ = "risk_inferences"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1", name="ck_risk_score_range"
        ),
    )

    inference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sectors.sector_id"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("model_versions.model_version_id"), nullable=True
    )
    prediction_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel, "risk_level_enum"), nullable=False
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)

    sector: Mapped["Sector"] = relationship(back_populates="risk_inferences")
    model_version: Mapped["ModelVersion | None"] = relationship(
        back_populates="risk_inferences"
    )
    feature_snapshot: Mapped["PredictionFeature | None"] = relationship(
        back_populates="inference",
        overlaps="inference",
        uselist=False,
        cascade="all, delete-orphan",
    )
    emergency_alerts: Mapped[list["EmergencyAlert"]] = relationship(
        back_populates="inference", cascade="all, delete-orphan"
    )
    risk_reviews: Mapped[list["RiskReview"]] = relationship(
        back_populates="inference", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RiskInference {self.sector_id} {self.risk_level}>"
