from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_dependency import require_admin
from database import SessionLocal, get_db
from models.users import User
from services import risk_run
from services.current_user import get_current_user

router = APIRouter(prefix="/api/v1/risk-runs", tags=["Daily risk run"])


def get_session_factory():
    return SessionLocal


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def start_risk_run(
    session_factory=Depends(get_session_factory),
    admin: User = Depends(require_admin),
):
    if not risk_run.start_in_background(session_factory):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A risk run is already in progress",
        )
    return {"started": True}


@router.get("/latest")
def latest_risk_run(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    last = risk_run.last_run(db)
    return {
        "running": risk_run.is_running(),
        "last_run": None
        if last is None
        else {
            "status": "FAILED" if last.action_type == risk_run.RUN_FAILED else "OK",
            "finished_at": last.created_at,
            "details": last.execution_details,
        },
    }
