import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import ModelStatus
from models._types import JSONVariant, enum_column, utcnow

if TYPE_CHECKING:
    from models.risk_inferences_model import RiskInference


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "model_name", "version_code", name="uq_model_versions_name_version"
        ),
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_code: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model_path: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_metrics: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    model_status: Mapped[ModelStatus] = mapped_column(
        enum_column(ModelStatus, "model_status_enum"),
        nullable=False,
        default=ModelStatus.TRAINING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    risk_inferences: Mapped[list["RiskInference"]] = relationship(
        back_populates="model_version"
    )

    def __repr__(self) -> str:
        return f"<ModelVersion {self.model_name}@{self.version_code}>"
