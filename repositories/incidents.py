from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.incident_reports import IncidentReport
from models.sectors import Sector
from models.system_audit_logs import SystemAuditLog


class IncidentRepository:
    def __init__(self):
        self.model = IncidentReport

    def _with_names(self):
        return select(self.model).options(
            joinedload(self.model.sector),
            joinedload(self.model.reported_by_user),
        )

    def sector_exists(self, db: Session, sector_id: UUID) -> bool:
        return db.get(Sector, sector_id) is not None

    def add_report(self, db: Session, report: IncidentReport) -> IncidentReport:
        db.add(report)
        db.flush()
        return report

    def add_audit_log(self, db: Session, log: SystemAuditLog) -> None:
        db.add(log)

    def get_report(self, db: Session, report_id: UUID) -> IncidentReport | None:
        query = self._with_names().where(self.model.report_id == report_id)
        return db.scalars(query).first()

    def list_reports(
        self, db: Session, limit: int, offset: int
    ) -> list[IncidentReport]:
        query = (
            self._with_names()
            .order_by(self.model.reported_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(db.scalars(query))


incident_repository = IncidentRepository()
