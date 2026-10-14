import uuid

from sqlalchemy import Column, Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import LandslideSeverity
from models._types import enum_column
from database import Base


class LandslideInventory(Base):
    __tablename__ = "landslide_inventory"

    landslide_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sector.sector_id"), nullable=False)
    event_date = Column(Date, nullable=False)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    severity = Column(
        enum_column(LandslideSeverity, "landslide_severity_enum"), nullable=True
    )
    source_name = Column(String(255), nullable=False)
    source_reference = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    sector = relationship("Sector", back_populates="landslide_inventory")
