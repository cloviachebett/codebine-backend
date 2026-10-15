import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import relationship

from models._types import utcnow
from database import Base


class AnalystShift(Base):
    __tablename__ = "analyst_shifts"
    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at > checked_in_at",
            name="ck_shift_checkout_after_checkin",
        ),
    )

    shift_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    analyst_id = Column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    checked_in_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Numeric(10, 2), nullable=True)

    analyst = relationship("User", back_populates="shifts")
