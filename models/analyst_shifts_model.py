import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._types import utcnow

if TYPE_CHECKING:
    from models.users_model import User


class AnalystShift(Base):
    __tablename__ = "analyst_shifts"
    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at > checked_in_at",
            name="ck_shift_checkout_after_checkin",
        ),
    )

    shift_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    analyst_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    analyst: Mapped["User"] = relationship(back_populates="shifts")

    def __repr__(self) -> str:
        state = "open" if self.checked_out_at is None else "closed"
        return f"<AnalystShift {self.analyst_id} ({state})>"
