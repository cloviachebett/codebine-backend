import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from database import Base


class RainfallMatrix(Base):
    __tablename__ = "rainfall_matrices"
    __table_args__ = (
        CheckConstraint(
            "rain_1day_mm >= 0 AND rain_3day_mm >= 0 AND rain_7day_mm >= 0 "
            "AND rain_10day_mm >= 0 AND rain_30day_mm >= 0",
            name="ck_rainfall_non_negative",
        ),
        UniqueConstraint(
            "sector_id", "observation_time", name="uq_rainfall_sector_time"
        ),
    )

    rainfall_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sectors.sector_id"), nullable=False)
    observation_time = Column(DateTime(timezone=True), nullable=False)
    rain_1day_mm = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_3day_mm = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_7day_mm = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_10day_mm = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_30day_mm = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    dataset_id = Column(Uuid, ForeignKey("dataset_metadata.dataset_id"), nullable=True)

    sector = relationship("Sector", back_populates="rainfall_matrices")
    dataset = relationship("DatasetMetadata", back_populates="rainfall_matrices")
