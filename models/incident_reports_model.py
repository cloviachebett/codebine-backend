import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import IncidentStatus
from models._types import enum_column, utcnow
from database import Base


class IncidentReport(Base):
    __tablename__ = "incident_report"

    report_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sector.sector_id"), nullable=False)
    reported_by = Column(Uuid, ForeignKey("user.user_id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    event_date = Column(Date, nullable=False)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=False)
    status = Column(
        enum_column(IncidentStatus, "incident_status_enum"),
        nullable=False,
        default=IncidentStatus.SUBMITTED,
    )

    sector = relationship("Sector", back_populates="incident_reports")
    reported_by_user = relationship("User", back_populates="incident_reports")
