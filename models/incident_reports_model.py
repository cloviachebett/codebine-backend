import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import IncidentStatus
from models._types import enum_column, utcnow

if TYPE_CHECKING:
    from models.sectors_model import Sector
    from models.users_model import User


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    sector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sectors.sector_id"), nullable=False
    )
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id"), nullable=True
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        enum_column(IncidentStatus, "incident_status_enum"),
        nullable=False,
        default=IncidentStatus.SUBMITTED,
    )

    sector: Mapped["Sector"] = relationship(back_populates="incident_reports")
    reported_by_user: Mapped["User | None"] = relationship(
        back_populates="incident_reports"
    )

    def __repr__(self) -> str:
        return f"<IncidentReport {self.report_id} {self.status.value}>"
