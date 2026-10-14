import uuid

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from models._enums import ModelStatus
from models._types import JSONVariant, enum_column, utcnow
from database import Base


class ModelVersion(Base):
    __tablename__ = "model_version"
    __table_args__ = (
        UniqueConstraint(
            "model_name", "version_code", name="uq_model_versions_name_version"
        ),
    )

    model_version_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    model_name = Column(String(255), nullable=False)
    version_code = Column(String(50), nullable=False)
    model_type = Column(String(100), nullable=False)
    model_path = Column(Text, nullable=False)
    evaluation_metrics = Column(JSONVariant, nullable=True)
    model_status = Column(
        enum_column(ModelStatus, "model_status_enum"),
        nullable=False,
        default=ModelStatus.TRAINING,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    risk_inferences = relationship("RiskInference", back_populates="model_version")
