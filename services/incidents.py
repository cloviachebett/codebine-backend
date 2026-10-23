from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.incident_reports import IncidentReport
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
) -> IncidentRead:
    if not incident_repository.sector_exists(db, data.sector_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown sector"
        )
    report = incident_repository.add_report(
        db,
        IncidentReport(
            sector_id=data.sector_id,
            reported_by=reporter_id,
            event_date=data.event_date,
            description=data.description,
        ),
    )
    db.commit()
    return get_incident(db, report.report_id)


def get_incident(db: Session, report_id: UUID) -> IncidentRead:
    report = incident_repository.get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident report not found"
        )
    return to_read(report)


def list_incidents(db: Session, limit: int, offset: int) -> list[IncidentRead]:
    return [
        to_read(report)
        for report in incident_repository.list_reports(db, limit, offset)
    ]
