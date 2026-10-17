from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.emergency_alerts import EmergencyAlert
from models.risk_inferences import RiskInference
from models.risk_reviews import RiskReview
from models.system_audit_logs import SystemAuditLog


class ReviewRepository:
    def __init__(self):
        self.model = RiskReview

    def _with_reviewer(self):
        return select(self.model).options(joinedload(self.model.reviewed_by_user))

    def get_alert(self, db: Session, alert_id: UUID) -> EmergencyAlert | None:
        return db.get(EmergencyAlert, alert_id)

    def get_inference(self, db: Session, inference_id: UUID) -> RiskInference | None:
        return db.get(RiskInference, inference_id)

    def add_review(self, db: Session, review: RiskReview) -> RiskReview:
        db.add(review)
        db.flush()
        return review

    def commit_with_audit_log(self, db: Session, log: SystemAuditLog) -> None:
        db.add(log)
        db.commit()

    def get_review(self, db: Session, review_id: UUID) -> RiskReview | None:
        query = self._with_reviewer().where(self.model.review_id == review_id)
        return db.scalars(query).first()

    def list_reviews(
        self,
        db: Session,
        alert_id: UUID | None,
        inference_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[RiskReview]:
        query = self._with_reviewer()
        if alert_id is not None:
            query = query.where(self.model.alert_id == alert_id)
        if inference_id is not None:
            query = query.where(self.model.inference_id == inference_id)
        query = (
            query.order_by(self.model.reviewed_at.desc()).limit(limit).offset(offset)
        )
        return list(db.scalars(query))


review_repository = ReviewRepository()
