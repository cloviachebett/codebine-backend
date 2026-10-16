from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models._enums import AlertStatus
from models.risk_reviews import RiskReview
from models.system_audit_logs import SystemAuditLog
from repositories.reviews import review_repository
from schemas.reviews import ReviewCreate, ReviewRead


def to_read(review: RiskReview) -> ReviewRead:
    return ReviewRead(
        review_id=review.review_id,
        inference_id=review.inference_id,
        alert_id=review.alert_id,
        decision=review.decision,
        comments=review.comments,
        reviewed_by=review.reviewed_by,
        reviewer_name=review.reviewed_by_user.full_name,
        reviewed_at=review.reviewed_at,
    )


def create_review(db: Session, data: ReviewCreate, reviewer_id: UUID) -> ReviewRead:
    if data.alert_id is not None:
        alert = review_repository.get_alert(db, data.alert_id)
        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )
        if alert.alert_status != AlertStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This alert has already been reviewed",
            )
        alert.alert_status = AlertStatus(data.decision.value)
    elif review_repository.get_inference(db, data.inference_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found"
        )

    review = review_repository.add_review(
        db,
        RiskReview(
            inference_id=data.inference_id,
            alert_id=data.alert_id,
            reviewed_by=reviewer_id,
            decision=data.decision,
            comments=data.comments or None,
        ),
    )
    review_repository.add_audit_log(
        db,
        SystemAuditLog(
            user_id=reviewer_id,
            action_type="RISK_REVIEW_CREATED",
            entity_type="risk_reviews",
            entity_id=str(review.review_id),
            execution_details={"decision": data.decision.value},
        ),
    )
    db.commit()
    return to_read(review_repository.get_review(db, review.review_id))


def list_reviews(
    db: Session,
    alert_id: UUID | None,
    inference_id: UUID | None,
    limit: int,
    offset: int,
) -> list[ReviewRead]:
    return [
        to_read(review)
        for review in review_repository.list_reviews(
            db, alert_id, inference_id, limit, offset
        )
    ]
