import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models._enums import AccountStatus, UserRole
from models._types import enum_column, utcnow

if TYPE_CHECKING:
    from models.analyst_shifts_model import AnalystShift
    from models.incident_reports_model import IncidentReport
    from models.risk_reviews_model import RiskReview
    from models.system_audit_logs_model import SystemAuditLog


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, "user_role_enum"),
        nullable=False,
        default=UserRole.ANALYST,
    )
    account_status: Mapped[AccountStatus] = mapped_column(
        enum_column(AccountStatus, "account_status_enum"),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mfa_enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > utcnow()

    @property
    def requires_mfa(self) -> bool:
        return self.role == UserRole.ADMIN

    shifts: Mapped[list["AnalystShift"]] = relationship(
        back_populates="analyst", cascade="all, delete-orphan"
    )
    incident_reports: Mapped[list["IncidentReport"]] = relationship(
        back_populates="reported_by_user"
    )
    risk_reviews: Mapped[list["RiskReview"]] = relationship(
        back_populates="reviewed_by_user"
    )
    audit_logs: Mapped[list["SystemAuditLog"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
