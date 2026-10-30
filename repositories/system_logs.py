import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from models.system_audit_logs import SystemAuditLog
from schemas.system_logs import AuditLogCreate


class AuditLogRepository:
    def __init__(self):
        self.model = SystemAuditLog

    def create(self, db: Session, schema: AuditLogCreate) -> SystemAuditLog:
        """Store a new audit record built from the incoming payload."""
        db_log = self.model(**schema.model_dump())
        db.add(db_log)
        db.flush()
        db.refresh(db_log)
        return db_log

    def get_by_id(self, db: Session, log_id: uuid.UUID) -> SystemAuditLog | None:
        """Return the audit record with the given id, or None when it is missing."""
        return db.query(self.model).filter(self.model.log_id == log_id).first()

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[SystemAuditLog]:
        """Return audit records newest first, inside the given page bounds."""
        return (
            db.query(self.model)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def save(self, db: Session, log: SystemAuditLog) -> None:
        db.add(log)
        db.commit()

    def exists_since(self, db: Session, action_type: str, since: datetime) -> bool:
        return (
            db.query(self.model.log_id)
            .filter(
                self.model.action_type == action_type,
                self.model.created_at >= since,
            )
            .first()
            is not None
        )


audit_log_repository = AuditLogRepository()
