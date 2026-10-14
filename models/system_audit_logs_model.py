import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._types import JSONVariant, utcnow

if TYPE_CHECKING:
    from models.users_model import User


class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_details: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<SystemAuditLog {self.action_type} {self.entity_type}>"
