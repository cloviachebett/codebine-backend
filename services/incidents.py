from uuid import UUID

from sqlalchemy.orm import Session

from models.incident_reports import IncidentReport
from models.system_audit_logs import SystemAuditLog
from repositories.incidents import incident_repository
from schemas.incidents import IncidentCreate, IncidentRead


def to_read(report: IncidentReport) -> IncidentRead:
    reporter = report.reported_by_user
    return IncidentRead(
        report_id=report.report_id,
        sector_id=report.sector_id,
        district_name=report.sector.district_name,
        sector_name=report.sector.sector_name,
        reported_by=report.reported_by,
        reporter_name=reporter.full_name if reporter else None,
        reported_at=report.reported_at,
        event_date=report.event_date,
        description=report.description,
    )


def create_incident(
    db: Session, data: IncidentCreate, reporter_id: UUID | None = None
) -> IncidentRead | None:
    if not incident_repository.sector_exists(db, data.sector_id):
        return None
    report = incident_repository.add_report(
        db,
        IncidentReport(
            sector_id=data.sector_id,
            reported_by=reporter_id,
            event_date=data.event_date,
            description=data.description,
        ),
    )
    incident_repository.add_audit_log(
        db,
        SystemAuditLog(
            user_id=reporter_id,
            action_type="INCIDENT_REPORT_CREATED",
            entity_type="incident_reports",
            entity_id=str(report.report_id),
        ),
    )
    db.commit()
    return get_incident(db, report.report_id)


def get_incident(db: Session, report_id: UUID) -> IncidentRead | None:
    report = incident_repository.get_report(db, report_id)
    return to_read(report) if report else None


def list_incidents(db: Session, limit: int, offset: int) -> list[IncidentRead]:
    return [
        to_read(report)
        for report in incident_repository.list_reports(db, limit, offset)
    ]
