from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.incident_reports import IncidentReport
from models.sectors import Sector
from models.system_audit_logs import SystemAuditLog


def _with_names():
    return select(IncidentReport).options(
        joinedload(IncidentReport.sector),
        joinedload(IncidentReport.reported_by_user),
    )


def sector_exists(db: Session, sector_id: UUID) -> bool:
    return db.get(Sector, sector_id) is not None


def add_report(db: Session, report: IncidentReport) -> IncidentReport:
    db.add(report)
    db.flush()
    return report


def add_audit_log(db: Session, log: SystemAuditLog) -> None:
    db.add(log)


def get_report(db: Session, report_id: UUID) -> IncidentReport | None:
    query = _with_names().where(IncidentReport.report_id == report_id)
    return db.scalars(query).first()


def list_reports(db: Session, limit: int, offset: int) -> list[IncidentReport]:
    query = (
        _with_names()
        .order_by(IncidentReport.reported_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query))
