from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.users import User
from schemas.reviews import ReviewCreate, ReviewRead
from services import reviews as review_service
from services.current_user import get_current_user

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_service.create_review(db, payload, user.user_id)


@router.get("", response_model=list[ReviewRead])
def list_reviews(
    alert_id: UUID | None = None,
    inference_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return review_service.list_reviews(db, alert_id, inference_id, limit, offset)
