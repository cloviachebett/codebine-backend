import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Sequence

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings as default_settings
from models._enums import DatasetFactorType, ProcessingStatus
from models.dataset_metadata import DatasetMetadata
from models.sectors import Sector
from models.system_audit_logs import SystemAuditLog
from repositories.rainfall_matrices import RainfallMatrixRepository, utc_date
from services.boundary import resolve_boundary_geometry
from services.chirps_gee import CHIRPSGEEService, SectorArea
from services.errors import (
    ChirpsFetchError,
    InvalidDateRangeError,
    InvalidGeometryError,
    SectorNotFoundError,
)
from services.geometry import compute_centroid
from services.rainfall_math import (
    WINDOW_DAYS,
    compute_rolling_windows,
    lookback_days,
    window_column,
)

logger = logging.getLogger(__name__)

DATASET_NAME = "CHIRPS daily rainfall (Google Earth Engine)"
DATASET_SOURCE = "CHIRPS - UCSB Climate Hazards Center"
DATASET_VERSION = "daily"


def _midnight_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


class RainfallService:
    def __init__(self, settings=None, chirps=None):
        self.rainfall_repository = RainfallMatrixRepository()
        self.settings = settings or default_settings
        self._chirps = (
            chirps  # injected in tests; otherwise a CHIRPS client is built per sync
        )

    def _get_chirps(self):
        return self._chirps or CHIRPSGEEService(settings=self.settings)

    def get_all_matrices(
        self,
        db: Session,
        sector_id: uuid.UUID | None = None,
        start: date | None = None,
        end: date | None = None,
        limit: int = 500,
    ):
        return self.rainfall_repository.get_all(
            db,
            sector_id=sector_id,
            start=_midnight_utc(start) if start else None,
            end_exclusive=_midnight_utc(end + timedelta(days=1)) if end else None,
            limit=limit,
        )

    def get_sector_matrix(
        self,
        db: Session,
        sector_id: uuid.UUID,
        start: date | None = None,
        end: date | None = None,
    ):
        if db.query(Sector).filter(Sector.sector_id == sector_id).first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sector {sector_id} was not found",
            )
        return self.rainfall_repository.get_by_sector(
            db,
            sector_id,
            start=_midnight_utc(start) if start else None,
            end_exclusive=_midnight_utc(end + timedelta(days=1)) if end else None,
        )

    def get_status(self, db: Session, include_chirps: bool = False) -> dict[str, Any]:
        stats = self.rainfall_repository.get_stats(db)
        latest = stats["latest_observation"]
        dataset = self._find_dataset(db)
        info: dict[str, Any] = {
            "stored_rows": stats["stored_rows"],
            "sectors_with_data": stats["sectors_with_data"],
            "latest_stored_date": utc_date(latest).isoformat() if latest else None,
            "dataset_status": dataset.processing_status.value if dataset else None,
            "last_synced_at": (
                dataset.last_processed_at.isoformat()
                if dataset and dataset.last_processed_at
                else None
            ),
        }
        if include_chirps:
            try:
                info["chirps_latest_available"] = (
                    self._get_chirps().latest_available_date().isoformat()
                )
            except ChirpsFetchError as exc:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY, detail=str(exc)
                ) from exc
        return info

    # sync from CHIRPS
    def sync_rainfall(
        self,
        db: Session,
        sector_ids: Sequence[uuid.UUID] | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, Any]:
        #HTTP-facing sync: runs ,run_sync and turns its errors into HTTP responses.
        if start and end and start > end:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="start_date is after end_date"
            )
        try:
            return self.run_sync(db, sector_ids=sector_ids, start=start, end=end)
        except SectorNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except (InvalidGeometryError, InvalidDateRangeError) as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except ChirpsFetchError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    def run_sync(
        self,
        db: Session,
        sector_ids: Sequence[uuid.UUID] | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, Any]:
        # Fetch daily CHIRPS, compute 1/3/7/10/30-day sums and upsert them per sector.

        # With no dates it refreshes the last rainfall_sync_lookback_days up to the newest day
        # CHIRPS has. Dates beyond what CHIRPS has published are clamped, never invented.
        # Raises domain errors (used directly by the scheduler and scripts).

        sectors = self._load_sectors(db, sector_ids)
        areas = [self._to_area(s) for s in sectors]

        chirps = self._get_chirps()
        latest = chirps.latest_available_date()
        requested_end = end or latest
        effective_end = min(requested_end, latest)
        if start is None:
            start = effective_end - timedelta(
                days=self.settings.rainfall_sync_lookback_days - 1
            )
        if start > effective_end:
            raise InvalidDateRangeError(
                f"start {start} is after the latest CHIRPS date available ({latest})"
            )

        dataset = self._begin_run(db)
        try:
            daily = chirps.fetch_daily_rainfall(
                areas, start - timedelta(days=lookback_days()), effective_end
            )
        except ChirpsFetchError as exc:
            self._finish_run(db, dataset, ok=False, details={"error": str(exc)})
            raise

        inserted = updated = skipped_days = 0
        sectors_incomplete: list[str] = []
        for sector in sectors:
            rows, skipped = compute_rolling_windows(
                daily.get(str(sector.sector_id), {}), start, effective_end
            )
            records = [
                {
                    "observation_time": _midnight_utc(r["observation_date"]),
                    **{window_column(n): r[window_column(n)] for n in WINDOW_DAYS},
                }
                for r in rows
            ]
            ins, upd = self.rainfall_repository.upsert_sector_rows(
                db, sector.sector_id, records, dataset.dataset_id
            )
            inserted += ins
            updated += upd
            skipped_days += len(skipped)
            if skipped:
                sectors_incomplete.append(str(sector.sector_id))

        summary = {
            "start_date": start.isoformat(),
            "end_date": effective_end.isoformat(),
            "requested_end_date": requested_end.isoformat(),
            "chirps_latest_available": latest.isoformat(),
            "clamped_to_latest_available": effective_end < requested_end,
            "sectors_synced": len(sectors),
            "rows_inserted": inserted,
            "rows_updated": updated,
            "days_skipped_incomplete": skipped_days,
            "sectors_with_missing_data": sectors_incomplete,
            "sector_days_without_chirps_value": len(getattr(chirps, "unresolved", [])),
        }
        self._finish_run(db, dataset, ok=True, details=summary)
        return summary

    # helpers
    def _load_sectors(self, db: Session, sector_ids) -> list[Sector]:
        query = db.query(Sector)
        if sector_ids:
            found = query.filter(Sector.sector_id.in_(list(sector_ids))).all()
            missing = set(sector_ids) - {s.sector_id for s in found}
            if missing:
                raise SectorNotFoundError(
                    "Sector(s) not found: " + ", ".join(sorted(str(m) for m in missing))
                )
            return found
        found = query.order_by(Sector.district_name, Sector.sector_name).all()
        if not found:
            raise SectorNotFoundError("There are no sectors to fetch rainfall for")
        return found

    def _to_area(self, sector: Sector) -> SectorArea:
        s = self.settings
        try:
            geometry = resolve_boundary_geometry(
                sector.boundary_ref,
                sector.sector_name,
                sector.district_name,
                base_dir=s.boundary_base_dir,
                sector_property=s.boundary_sector_property,
                district_property=s.boundary_district_property,
            )
        except InvalidGeometryError as exc:
            raise InvalidGeometryError(
                f"Sector {sector.sector_name} ({sector.sector_id}): {exc}"
            ) from exc
        lat, lon = compute_centroid(geometry)
        return SectorArea(str(sector.sector_id), geometry, lat, lon)

    def _find_dataset(self, db: Session) -> DatasetMetadata | None:
        return (
            db.query(DatasetMetadata)
            .filter(
                DatasetMetadata.dataset_name == DATASET_NAME,
                DatasetMetadata.version == DATASET_VERSION,
            )
            .first()
        )

    def _begin_run(self, db: Session) -> DatasetMetadata:
        dataset = self._find_dataset(db)
        if dataset is None:
            dataset = DatasetMetadata(
                dataset_name=DATASET_NAME,
                factor_type=DatasetFactorType.RAINFALL,
                source_name=DATASET_SOURCE,
                file_path=self.settings.chirps_collection,
                version=DATASET_VERSION,
            )
            db.add(dataset)
        dataset.processing_status = ProcessingStatus.PROCESSING
        db.commit()
        db.refresh(dataset)
        return dataset

    def _finish_run(
        self, db: Session, dataset: DatasetMetadata, ok: bool, details: dict[str, Any]
    ) -> None:
        dataset.processing_status = (
            ProcessingStatus.READY if ok else ProcessingStatus.FAILED
        )
        if ok:
            dataset.last_processed_at = datetime.now(timezone.utc)
        db.add(
            SystemAuditLog(
                action_type="RAINFALL_SYNC_SUCCESS" if ok else "RAINFALL_SYNC_FAILED",
                entity_type="dataset_metadata",
                entity_id=str(dataset.dataset_id),
                execution_details=details,
            )
        )
        db.commit()


rainfall_service = RainfallService()
