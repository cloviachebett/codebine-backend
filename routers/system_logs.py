import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from schemas.system_logs import AuditLogResponse
from services import system_logs as system_log_service
from services.current_user import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["System Audit Logs"])


@router.get("/", response_model=list[AuditLogResponse])
def list_all_system_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches a list of all audit records from the database."""
    return system_log_service.list_all_system_logs(
        db, current_user, skip=skip, limit=limit
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_single_system_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches a single unique audit record by its ID number."""
    return system_log_service.get_single_system_log(db, log_id, current_user)
