import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import relationship

from models._enums import RiskLevel
from models._types import enum_column, utcnow
from database import Base


class RiskInference(Base):
    __tablename__ = "risk_inferences"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1", name="ck_risk_score_range"
        ),
    )

    inference_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sectors.sector_id"), nullable=False)
    model_version_id = Column(
        Uuid, ForeignKey("model_versions.model_version_id"), nullable=False
    )
    prediction_time = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    risk_level = Column(enum_column(RiskLevel, "risk_level_enum"), nullable=False)
    risk_score = Column(Numeric(6, 5), nullable=False)
    feature_snapshot_id = Column(Uuid, nullable=True, index=True)

    sector = relationship("Sector", back_populates="risk_inferences")
    model_version = relationship("ModelVersion", back_populates="risk_inferences")
    feature_snapshot = relationship(
        "PredictionFeature",
        back_populates="inference",
        overlaps="inference",
        uselist=False,
        cascade="all, delete-orphan",
    )
    emergency_alerts = relationship(
        "EmergencyAlert", back_populates="inference", cascade="all, delete-orphan"
    )
    risk_reviews = relationship(
        "RiskReview", back_populates="inference", cascade="all, delete-orphan"
    )
