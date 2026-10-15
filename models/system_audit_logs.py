import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from models._types import JSONVariant, utcnow
from database import Base


class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"

    log_id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.user_id"), nullable=True)
    action_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(64), nullable=True)
    execution_details = Column(JSONVariant, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="audit_logs")
