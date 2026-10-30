from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from auth_dependency import require_admin
from database import get_db
from models._enums import AlertStatus
from models.users import User
from schemas.alerts import AlertCreate, AlertRead
from services import alerts as alert_service

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return alert_service.create_alert(db, payload)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    alert_status: AlertStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return alert_service.list_alerts(db, alert_status, limit, offset)


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: UUID, db: Session = Depends(get_db)):
    return alert_service.get_alert(db, alert_id)
