import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import LandslideSeverity
from models._types import enum_column

if TYPE_CHECKING:
    from models.sectors_model import Sector


class LandslideInventory(Base):
    __tablename__ = "landslide_inventory"

    landslide_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sectors.sector_id"), nullable=False
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    severity: Mapped[LandslideSeverity | None] = mapped_column(
        enum_column(LandslideSeverity, "landslide_severity_enum"), nullable=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sector: Mapped["Sector"] = relationship(back_populates="landslide_inventory")

    def __repr__(self) -> str:
        return f"<LandslideInventory {self.event_date} {self.sector_id}>"
