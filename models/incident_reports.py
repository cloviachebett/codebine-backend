import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import relationship

from models._enums import IncidentStatus
from models._types import enum_column, utcnow
from database import Base


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    report_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sectors.sector_id"), nullable=False)
    reported_by = Column(Uuid, ForeignKey("users.user_id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    event_date = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    description = Column(String, nullable=False)
    status = Column(
        enum_column(IncidentStatus, "incident_status_enum"),
        nullable=False,
        default=IncidentStatus.SUBMITTED,
    )

    sector = relationship("Sector", back_populates="incident_reports")
    reported_by_user = relationship("User", back_populates="incident_reports")
