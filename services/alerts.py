from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models._enums import AlertSeverity, AlertStatus, RiskLevel
from models.emergency_alerts import EmergencyAlert
from models.system_audit_logs import SystemAuditLog
from repositories.alerts import alert_repository
from schemas.alerts import AlertCreate, AlertRead

SEVERITY_FOR_RISK = {
    RiskLevel.HIGH: AlertSeverity.HIGH,
    RiskLevel.EXTREME: AlertSeverity.CRITICAL,
}


def to_read(alert: EmergencyAlert) -> AlertRead:
    return AlertRead(
        alert_id=alert.alert_id,
        inference_id=alert.inference_id,
        sector_id=alert.sector_id,
        district_name=alert.sector.district_name,
        sector_name=alert.sector.sector_name,
        risk_level=alert.inference.risk_level,
        risk_score=alert.inference.risk_score,
        severity=alert.severity,
        alert_message=alert.alert_message,
        alert_status=alert.alert_status,
        created_at=alert.created_at,
    )


def create_alert(db: Session, data: AlertCreate) -> AlertRead:
    inference = alert_repository.get_inference(db, data.inference_id)
    if inference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found"
        )
    severity = SEVERITY_FOR_RISK.get(inference.risk_level)
    if severity is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only HIGH or EXTREME predictions can be flagged",
        )
    if alert_repository.exists_for_inference(db, inference.inference_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An alert already exists for this prediction",
        )
    sector = inference.sector
    alert = alert_repository.add_alert(
        db,
        EmergencyAlert(
            inference_id=inference.inference_id,
            sector_id=inference.sector_id,
            severity=severity,
            alert_message=(
                f"{inference.risk_level.value} landslide risk predicted for "
                f"{sector.sector_name} ({sector.district_name}). Review required."
            ),
        ),
    )
    alert_repository.add_audit_log(
        db,
        SystemAuditLog(
            action_type="EMERGENCY_ALERT_CREATED",
            entity_type="emergency_alerts",
            entity_id=str(alert.alert_id),
        ),
    )
    db.commit()
    return get_alert(db, alert.alert_id)


def get_alert(db: Session, alert_id: UUID) -> AlertRead:
    alert = alert_repository.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    return to_read(alert)


def list_alerts(
    db: Session, alert_status: AlertStatus | None, limit: int, offset: int
) -> list[AlertRead]:
    return [
        to_read(alert)
        for alert in alert_repository.list_alerts(db, alert_status, limit, offset)
    ]
