import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.sectors_model import Sector


class RainfallMatrix(Base):
    __tablename__ = "rainfall_matrices"
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

    rainfall_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sectors.sector_id"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    rain_1day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.0")
    )
    rain_3day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.0")
    )
    rain_7day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.0")
    )
    rain_10day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.0")
    )
    rain_30day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.0")
    )

    sector: Mapped["Sector"] = relationship(back_populates="rainfall_matrices")

    def __repr__(self) -> str:
        return f"<RainfallMatrix {self.sector_id} {self.observation_date}>"
