import logging
import time
import uuid
from contextlib import contextmanager, suppress
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from database import get_db
from models._enums import UserRole
from models.users import User
from repositories.system_logs import audit_log_repository
from schemas.system_logs import AuditLogCreate, AuditLogResponse

logger = logging.getLogger(__name__)


@contextmanager
def _session_for(request: Request):
    """Safely yields an isolated DB session context, preventing connection leaks."""
    override = request.app.dependency_overrides.get(get_db)
    if override is not None:
        res = override()
        if hasattr(res, "__enter__"):
            with res as session:
                yield session
        else:
            yield res
        return

    ctx = get_db()
    try:
        session = next(ctx)
        yield session
    finally:
        with suppress(StopIteration):
            next(ctx)


def ensure_admin(user: User) -> None:
    """Reject callers that are not administrators."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted. Administrative privileges required.",
        )


def log_action(db: Session, schema: AuditLogCreate) -> AuditLogResponse:
    """Persist an audit record using flush to avoid damaging external transactions."""
    db_log = audit_log_repository.create(db, schema)
    db.flush()
    return AuditLogResponse.model_validate(db_log)


def log_manual_audit_record(
    db: Session, schema: AuditLogCreate, user: User
) -> AuditLogResponse:
    """Persist an admin created audit record attributed to the acting admin."""
    ensure_admin(user)
    schema.user_id = user.user_id
    response = log_action(db, schema)
    db.commit()
    return response


def log_system_event(
    db: Session,
    action_type: str,
    entity_type: str,
    user_id: Optional[uuid.UUID] = None,
    entity_id: Optional[str] = None,
    execution_details: Optional[Dict[str, Any]] = None,
) -> AuditLogResponse:
    """Persist an audit record for an event raised by the system itself."""
    payload = AuditLogCreate(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        execution_details=execution_details,
    )
    return log_action(db, payload)


def fetch_log(db: Session, log_id: uuid.UUID) -> AuditLogResponse:
    """Return one audit record, or report that it does not exist."""
    db_log = audit_log_repository.get_by_id(db, log_id)
    if db_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found.",
        )
    return AuditLogResponse.model_validate(db_log)


def list_logs(db: Session, skip: int = 0, limit: int = 100) -> list[AuditLogResponse]:
    """Return audit records newest first, inside the given page bounds."""
    return [
        AuditLogResponse.model_validate(log)
        for log in audit_log_repository.get_multi(db, skip=skip, limit=limit)
    ]


def get_single_system_log(
    db: Session, log_id: uuid.UUID, user: User
) -> AuditLogResponse:
    """Return one audit record to an administrator."""
    ensure_admin(user)
    return fetch_log(db, log_id)


def list_all_system_logs(
    db: Session, user: User, skip: int = 0, limit: int = 100
) -> list[AuditLogResponse]:
    """Return every audit record to an administrator."""
    ensure_admin(user)
    return list_logs(db, skip=skip, limit=limit)


class AutomatedAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        try:
            user_id = None
            if getattr(request.state, "user", None):
                user_id = getattr(request.state.user, "user_id", None)

            path_tag = request.url.path.strip("/").replace("/", "_").upper()
            action_tag = f"API_{request.method}_{path_tag if path_tag else 'ROOT'}"

            execution_details = {
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration_seconds": round(process_time, 4),
            }

            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                self._persist_audit_log_background,
                request=request,
                action_type=action_tag[:100],
                user_id=user_id,
                status_code=str(response.status_code),
                execution_details=execution_details,
            )
            response.background = background_tasks

        except Exception:
            logger.exception(
                "Failed to schedule background audit log for: %s %s",
                request.method,
                request.url.path,
            )

        return response

    def _persist_audit_log_background(
        self,
        request: Request,
        action_type: str,
        user_id: Any,
        status_code: str,
        execution_details: dict,
    ):
        """Asynchronously persists the mutation data using an isolated context."""
        try:
            with _session_for(request) as db:
                log_system_event(
                    db=db,
                    action_type=action_type,
                    entity_type="api_routes",
                    user_id=user_id,
                    entity_id=status_code,
                    execution_details=execution_details,
                )
                db.commit()
        except Exception:
            logger.exception("Background worker failed to write system audit log.")
