import uuid

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from models._types import JSONVariant, utcnow
from database import Base


class PredictionFeature(Base):
    __tablename__ = "prediction_feature"
    __table_args__ = (
        UniqueConstraint("inference_id", name="uq_prediction_features_inference"),
    )

    feature_snapshot_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    inference_id = Column(
        Uuid, ForeignKey("risk_inference.inference_id"), nullable=False
    )
    historical_features = Column(JSONVariant, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    inference = relationship(
        "RiskInference",
        back_populates="feature_snapshot",
        overlaps="inference",
    )
