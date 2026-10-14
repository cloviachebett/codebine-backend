import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import GeologyClass
from models._types import JSONVariant, enum_column, utcnow

if TYPE_CHECKING:
    from models.emergency_alerts_model import EmergencyAlert
    from models.incident_reports_model import IncidentReport
    from models.landslide_inventory_model import LandslideInventory
    from models.rainfall_matrices_model import RainfallMatrix
    from models.risk_inferences_model import RiskInference


class Sector(Base):
    __tablename__ = "sectors"
    __table_args__ = (
        CheckConstraint("mean_slope_deg >= 0", name="ck_sectors_slope_non_negative"),
        UniqueConstraint(
            "district_name", "sector_name", name="uq_sectors_district_sector"
        ),
    )

    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    province_name: Mapped[str] = mapped_column(String(50), nullable=False)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(50), nullable=False)
    boundary_ref: Mapped[str] = mapped_column(Text, nullable=False)
    mean_slope_deg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    geology_class: Mapped[GeologyClass] = mapped_column(
        enum_column(GeologyClass, "geology_class_enum"), nullable=False
    )
    soil_features: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    land_cover_class: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    rainfall_matrices: Mapped[list["RainfallMatrix"]] = relationship(
        back_populates="sector", cascade="all, delete-orphan"
    )
    landslide_inventory: Mapped[list["LandslideInventory"]] = relationship(
        back_populates="sector", cascade="all, delete-orphan"
    )
    risk_inferences: Mapped[list["RiskInference"]] = relationship(
        back_populates="sector", cascade="all, delete-orphan"
    )
    emergency_alerts: Mapped[list["EmergencyAlert"]] = relationship(
        back_populates="sector", cascade="all, delete-orphan"
    )
    incident_reports: Mapped[list["IncidentReport"]] = relationship(
        back_populates="sector", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Sector {self.district_name}/{self.sector_name}>"
