from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.rainfall_matrices import RainfallMatrix


def utc_date(value: datetime) -> date:
    # Calendar date of a stored timestamp, independent of the DB session time zone.
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.date()


class RainfallMatrixRepository:
    def __init__(self):
        self.model = RainfallMatrix

    def get_all(
        self,
        db: Session,
        sector_id: UUID | None = None,
        start: datetime | None = None,
        end_exclusive: datetime | None = None,
        limit: int = 500,
    ):
        query = db.query(self.model)
        if sector_id is not None:
            query = query.filter(self.model.sector_id == sector_id)
        if start is not None:
            query = query.filter(self.model.observation_time >= start)
        if end_exclusive is not None:
            query = query.filter(self.model.observation_time < end_exclusive)
        return query.order_by(self.model.observation_time.desc()).limit(limit).all()

    def get_by_sector(
        self,
        db: Session,
        sector_id: UUID,
        start: datetime | None = None,
        end_exclusive: datetime | None = None,
        limit: int = 5000,
    ):
        query = db.query(self.model).filter(self.model.sector_id == sector_id)
        if start is not None:
            query = query.filter(self.model.observation_time >= start)
        if end_exclusive is not None:
            query = query.filter(self.model.observation_time < end_exclusive)
        return query.order_by(self.model.observation_time.asc()).limit(limit).all()

    def upsert_sector_rows(
        self,
        db: Session,
        sector_id: UUID,
        rows: list[dict[str, Any]],
        dataset_id: UUID | None = None,
    ) -> tuple[int, int]:
        # Insert new (sector, day) rows and update existing ones.

        # Returns (inserted, updated). Only the days in rows are touched.

        if not rows:
            return 0, 0
        times = [r["observation_time"] for r in rows]
        existing = {
            utc_date(x.observation_time): x
            for x in db.query(self.model).filter(
                self.model.sector_id == sector_id,
                self.model.observation_time >= min(times),
                self.model.observation_time <= max(times),
            )
        }
        inserted = updated = 0
        for row in rows:
            current = existing.get(utc_date(row["observation_time"]))
            if current is None:
                db.add(self.model(sector_id=sector_id, dataset_id=dataset_id, **row))
                inserted += 1
            else:
                for key, value in row.items():
                    setattr(current, key, value)
                current.dataset_id = dataset_id
                updated += 1
        db.flush()
        return inserted, updated

    def get_stats(self, db: Session) -> dict[str, Any]:
        rows, latest, sectors = db.query(
            func.count(self.model.rainfall_id),
            func.max(self.model.observation_time),
            func.count(func.distinct(self.model.sector_id)),
        ).one()
        return {
            "stored_rows": rows,
            "latest_observation": latest,
            "sectors_with_data": sectors,
        }


rainfall_matrix_repository = RainfallMatrixRepository()
