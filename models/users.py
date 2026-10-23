import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import relationship

from models._enums import AccountStatus, UserRole
from models._types import enum_column, utcnow
from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(
        enum_column(UserRole, "user_role_enum"),
        nullable=False,
        default=UserRole.ANALYST,
    )
    account_status = Column(
        enum_column(AccountStatus, "account_status_enum"),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    phone = Column(String(30), nullable=True)
    mfa_enrolled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(String(64), nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token_hash = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    reset_token_hash = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    shifts = relationship(
        "AnalystShift", back_populates="analyst", cascade="all, delete-orphan"
    )
    incident_reports = relationship("IncidentReport", back_populates="reported_by_user")
    risk_reviews = relationship("RiskReview", back_populates="reviewed_by_user")
    audit_logs = relationship("SystemAuditLog", back_populates="user")

    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > utcnow()

    @property
    def requires_mfa(self) -> bool:
        return self.role == UserRole.ADMIN
