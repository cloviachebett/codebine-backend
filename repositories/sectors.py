import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.emergency_alerts import EmergencyAlert
from models.incident_reports import IncidentReport
from models.landslide_inventory import LandslideInventory
from models.rainfall_matrices import RainfallMatrix
from models.risk_inferences import RiskInference
from models.sectors import Sector


class SectorRepository:
    def __init__(self):
        self.model = Sector

    def get(self, db: Session, sector_id: uuid.UUID):
        return db.get(self.model, sector_id)

    def get_all(
        self,
        db: Session,
        province_name: str | None = None,
        district_name: str | None = None,
        skip: int = 0,
        limit: int | None = None,
    ):
        query = db.query(self.model)
        if province_name is not None:
            query = query.filter(self.model.province_name == province_name)
        if district_name is not None:
            query = query.filter(self.model.district_name == district_name)
        query = query.order_by(
            self.model.province_name, self.model.district_name, self.model.sector_name
        )
        return query.offset(skip).limit(limit).all()

    def get_many(self, db: Session, sector_ids: list[uuid.UUID]) -> list[Sector]:
        return db.query(self.model).filter(self.model.sector_id.in_(sector_ids)).all()

    def get_by_location(self, db: Session, district_name: str, sector_name: str):
        return (
            db.query(self.model)
            .filter(
                self.model.district_name == district_name,
                self.model.sector_name == sector_name,
            )
            .first()
        )

    def count_linked_records(self, db: Session, sector_id: uuid.UUID) -> dict[str, int]:
        """How many rows in each table still point at this sector."""
        linked = {
            "rainfall_matrices": RainfallMatrix,
            "landslide_inventory": LandslideInventory,
            "risk_inferences": RiskInference,
            "emergency_alerts": EmergencyAlert,
            "incident_reports": IncidentReport,
        }
        return {
            name: db.query(func.count(model.sector_id))
            .filter(model.sector_id == sector_id)
            .scalar()
            for name, model in linked.items()
        }

    def create(self, db: Session, sector: Sector):
        db.add(sector)
        db.commit()
        db.refresh(sector)
        return sector

    def update(self, db: Session, sector: Sector):
        db.commit()
        db.refresh(sector)
        return sector

    def delete(self, db: Session, sector: Sector):
        db.delete(sector)
        db.commit()


sector_repository = SectorRepository()
