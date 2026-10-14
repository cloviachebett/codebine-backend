import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._types import JSONVariant, utcnow

if TYPE_CHECKING:
    from models.risk_inferences_model import RiskInference


class PredictionFeature(Base):
    __tablename__ = "prediction_features"
    __table_args__ = (
        UniqueConstraint("inference_id", name="uq_prediction_features_inference"),
    )

    feature_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    inference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("risk_inferences.inference_id"), nullable=False
    )
    historical_features: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    inference: Mapped["RiskInference"] = relationship(
        back_populates="feature_snapshot",
        overlaps="inference",
    )

    def __repr__(self) -> str:
        return f"<PredictionFeature {self.feature_snapshot_id}>"
