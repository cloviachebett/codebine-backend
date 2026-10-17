from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models._enums import AlertStatus
from models.emergency_alerts import EmergencyAlert
from models.risk_inferences import RiskInference
from models.system_audit_logs import SystemAuditLog


class AlertRepository:
    def __init__(self):
        self.model = EmergencyAlert

    def _with_details(self):
        return select(self.model).options(
            joinedload(self.model.sector),
            joinedload(self.model.inference),
        )

    def get_inference(self, db: Session, inference_id: UUID) -> RiskInference | None:
        query = (
            select(RiskInference)
            .options(joinedload(RiskInference.sector))
            .where(RiskInference.inference_id == inference_id)
        )
        return db.scalars(query).first()

    def exists_for_inference(self, db: Session, inference_id: UUID) -> bool:
        query = select(self.model.alert_id).where(
            self.model.inference_id == inference_id
        )
        return db.scalars(query).first() is not None

    def add_alert(self, db: Session, alert: EmergencyAlert) -> EmergencyAlert:
        db.add(alert)
        db.flush()
        return alert

    def commit_with_audit_log(self, db: Session, log: SystemAuditLog) -> None:
        db.add(log)
        db.commit()

    def get_alert(self, db: Session, alert_id: UUID) -> EmergencyAlert | None:
        query = self._with_details().where(self.model.alert_id == alert_id)
        return db.scalars(query).first()

    def list_alerts(
        self, db: Session, alert_status: AlertStatus | None, limit: int, offset: int
    ) -> list[EmergencyAlert]:
        query = self._with_details()
        if alert_status is not None:
            query = query.where(self.model.alert_status == alert_status)
        query = query.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        return list(db.scalars(query))


alert_repository = AlertRepository()
