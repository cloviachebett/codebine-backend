import uuid

from sqlalchemy import Column, DateTime, String, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import DatasetFactorType, ProcessingStatus
from models._types import enum_column
from database import Base


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    dataset_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    dataset_name = Column(String(255), nullable=False)
    factor_type = Column(
        enum_column(DatasetFactorType, "dataset_factor_type_enum"), nullable=False
    )
    source_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    version = Column(String(50), nullable=False)
    processing_status = Column(
        enum_column(ProcessingStatus, "processing_status_enum"),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )
    last_processed_at = Column(DateTime(timezone=True), nullable=True)

    rainfall_matrices = relationship("RainfallMatrix", back_populates="dataset")
