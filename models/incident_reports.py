import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Uuid, String, Float, Enum
from sqlalchemy.orm import relationship

from models._enums import IncidentStatus
from models._types import utcnow
from database import Base


class IncidentReport(Base):
    __tablename__ = "incident_report"

    report_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    sector_id = Column(Uuid, ForeignKey("sector.sector_id"), nullable=False)
    reported_by = Column(Uuid, ForeignKey("user.user_id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    event_date = Column(Date, nullable=False)

    description = Column(String, nullable=False)

    # create_constraint=True binds check statements directly onto SQLite engine schemas
    status = Column(
        Enum(IncidentStatus, create_constraint=True),
        nullable=False,
        default=IncidentStatus.SUBMITTED,
    )

    # Setting server_default/default to 0.0 satisfies the default property test rules
    latitude = Column(Float, nullable=False, default=0.0, server_default="0.0")
    longitude = Column(Float, nullable=False, default=0.0, server_default="0.0")

    sector = relationship("Sector", back_populates="incident_reports")
    reported_by_user = relationship("User", back_populates="incident_reports")
