import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from models._enums import GeologyClass
from models._types import JSONVariant, enum_column, utcnow
from database import Base


class Sector(Base):
    __tablename__ = "sectors"
    __table_args__ = (
        CheckConstraint("mean_slope_deg >= 0", name="ck_sectors_slope_non_negative"),
        UniqueConstraint(
            "district_name", "sector_name", name="uq_sectors_district_sector"
        ),
    )

    sector_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    province_name = Column(String(50), nullable=False)
    district_name = Column(String(100), nullable=False)
    sector_name = Column(String(50), nullable=False)
    boundary_ref = Column(Text, nullable=False)
    mean_slope_deg = Column(Numeric(5, 2), nullable=False)
    geology_class = Column(
        enum_column(GeologyClass, "geology_class_enum"), nullable=False
    )
    soil_features = Column(JSONVariant, nullable=False)
    land_cover_class = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    rainfall_matrices = relationship(
        "RainfallMatrix", back_populates="sector", cascade="all, delete-orphan"
    )

    landslide_inventory = relationship(
        "LandslideInventory", back_populates="sector", cascade="all, delete-orphan"
    )

    risk_inferences = relationship(
        "RiskInference", back_populates="sector", cascade="all, delete-orphan"
    )
    emergency_alerts = relationship(
        "EmergencyAlert", back_populates="sector", cascade="all, delete-orphan"
    )

    incident_reports = relationship(
        "IncidentReport", back_populates="sector", cascade="all, delete-orphan"
    )
