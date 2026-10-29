from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from schemas.incidents import IncidentCreate, IncidentRead
from services import incidents as incident_service
from services.current_user import get_current_user

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return incident_service.create_incident(db, payload, user.user_id)


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return incident_service.list_incidents(db, limit, offset)


@router.get("/{report_id}", response_model=IncidentRead)
def get_incident(report_id: UUID, db: Session = Depends(get_db)):
    return incident_service.get_incident(db, report_id)
