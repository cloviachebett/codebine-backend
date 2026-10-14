import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from database import Base


class RainfallMatrix(Base):
    __tablename__ = "rainfall_matrix_table"
    __table_args__ = (
        CheckConstraint(
            "rain_1day >= 0 AND rain_3day >= 0 AND rain_7day >= 0 "
            "AND rain_10day >= 0 AND rain_30day >= 0",
            name="ck_rainfall_non_negative",
        ),
        UniqueConstraint(
            "sector_id", "observation_date", name="uq_rainfall_sector_date"
        ),
    )

    rainfall_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sector.sector_id"), nullable=False)
    observation_date = Column(Date, nullable=False)
    rain_1day = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_3day = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_7day = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_10day = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))
    rain_30day = Column(Numeric(6, 2), nullable=False, default=Decimal("0.0"))

    sector = relationship("Sector", back_populates="rainfall_matrices")
