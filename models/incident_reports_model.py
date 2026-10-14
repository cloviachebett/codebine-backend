import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import IncidentStatus
from models._types import enum_column, utcnow
from database import Base


class IncidentReport(Base):
    __tablename__ = "incident_report_table"

    report_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sector_table.sector_id"), nullable=False)
    reported_by = Column(Uuid, ForeignKey("user_table.user_id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    event_date = Column(Date, nullable=False)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    description = Column(Text, nullable=False)
    status = Column(
        enum_column(IncidentStatus, "incident_status_enum"),
        nullable=False,
        default=IncidentStatus.SUBMITTED,
    )

    sector = relationship("Sector", back_populates="incident_reports")
    reported_by_user = relationship("User", back_populates="incident_reports")
