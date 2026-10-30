import logging
import os
import threading
from datetime import datetime, time, timezone
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models._enums import RiskLevel
from models.rainfall_matrices import RainfallMatrix
from models.system_audit_logs import SystemAuditLog
from repositories.rainfall_matrices import rainfall_matrix_repository
from repositories.risk_inference_repository import risk_inference_repository
from repositories.sectors import sector_repository
from repositories.system_logs import audit_log_repository
from schemas.alerts import AlertCreate
from services import alerts as alert_service
from services import storage
from services.model_version_service import ModelVersionService
from services.rainfall_matrices import rainfall_service

logger = logging.getLogger(__name__)

ALERT_LEVELS = {RiskLevel.HIGH, RiskLevel.EXTREME}
WINDOWS = (
    "rain_1day_mm",
    "rain_3day_mm",
    "rain_7day_mm",
    "rain_10day_mm",
    "rain_30day_mm",
)
RUN_OK = "DAILY_RISK_RUN"
RUN_FAILED = "DAILY_RISK_RUN_FAILED"

_running = threading.Lock()


def _start_of_today() -> datetime:
    return datetime.combine(
        datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc
    )


def _observation(row: RainfallMatrix) -> dict[str, Any]:
    observed = row.observation_time
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return {
        "observation_time": observed.isoformat(),
        **{name: float(getattr(row, name)) for name in WINDOWS},
    }


def _sync_rainfall(db: Session, rainfall) -> dict[str, Any]:
    try:
        return (rainfall or rainfall_service).run_sync(db)
    except Exception as exc:
        rainfall_matrix_repository.rollback(db)
        logger.warning("Rainfall sync failed, using stored rainfall: %s", exc)
        return {"error": str(exc)}


def run_daily_risk(db: Session, sync: bool = True, rainfall=None) -> dict[str, Any]:
    summary: dict[str, Any] = {"started_at": datetime.now(timezone.utc).isoformat()}
    if sync:
        summary["rainfall"] = _sync_rainfall(db, rainfall)

    model = ModelVersionService(db).active_model()
    rain = rainfall_matrix_repository.latest_per_sector(db)
    done_today = risk_inference_repository.sector_ids_predicted_since(
        db, model.model_version_id, _start_of_today()
    )
    predictor = ModelVersionService(db)

    levels = {level.value: 0 for level in RiskLevel}
    alerts_created = 0
    skipped_no_rainfall = 0
    skipped_already_done = 0
    failed: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []

    for sector in sector_repository.get_all(db):
        row = rain.get(sector.sector_id)
        if row is None:
            skipped_no_rainfall += 1
            continue
        if sector.sector_id in done_today:
            skipped_already_done += 1
            continue
        observation = _observation(row)
        try:
            result = predictor.predict_from_rainfall(
                model.model_version_id, sector.sector_id, [observation]
            )
            level = RiskLevel(result["risk_level"])
            levels[level.value] += 1
            if level in ALERT_LEVELS:
                alert_service.create_alert(
                    db, AlertCreate(inference_id=result["inference_id"])
                )
                alerts_created += 1
            results.append(
                {
                    "sector_id": str(sector.sector_id),
                    "sector_name": sector.sector_name,
                    "district_name": sector.district_name,
                    "risk_level": level.value,
                    "risk_score": result["risk_score"],
                    **observation,
                }
            )
        except HTTPException as exc:
            risk_inference_repository.rollback(db)
            failed.append({"sector": sector.sector_name, "error": str(exc.detail)})

    summary.update(
        {
            "model_version_id": str(model.model_version_id),
            "predictions": sum(levels.values()),
            "risk_levels": levels,
            "alerts_created": alerts_created,
            "sectors_without_rainfall": skipped_no_rainfall,
            "sectors_already_predicted_today": skipped_already_done,
            "failed": failed,
        }
    )
    summary["archive"] = storage.save_daily_run(summary, results)
    audit_log_repository.save(
        db,
        SystemAuditLog(
            action_type=RUN_OK,
            entity_type="risk_inferences",
            entity_id=str(model.model_version_id),
            execution_details=summary,
        ),
    )
    return summary


def ran_today(db: Session) -> bool:
    return audit_log_repository.exists_since(db, RUN_OK, _start_of_today())


def _record_failure(session_factory: Callable[[], Session], error: Exception) -> None:
    db = session_factory()
    try:
        audit_log_repository.save(
            db,
            SystemAuditLog(
                action_type=RUN_FAILED,
                entity_type="risk_inferences",
                execution_details={"error": str(error)},
            ),
        )
    finally:
        db.close()


def _run_and_release(session_factory: Callable[[], Session]) -> None:
    try:
        db = session_factory()
        try:
            run_daily_risk(db)
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Daily risk run failed")
        _record_failure(session_factory, exc)
    finally:
        _running.release()


def run_with_lock(session_factory: Callable[[], Session]) -> bool:
    if not _running.acquire(blocking=False):
        return False
    _run_and_release(session_factory)
    return True


def auto_run_enabled() -> bool:
    return os.getenv("DAILY_RISK_RUN", "").lower() in {"1", "true", "yes"}


def start_auto_runner(
    session_factory: Callable[[], Session],
    stop: threading.Event,
    first_check_seconds: float = 60,
    check_every_seconds: float = 3600,
) -> threading.Thread:
    def loop():
        wait = first_check_seconds
        while not stop.wait(wait):
            wait = check_every_seconds
            db = session_factory()
            try:
                due = not ran_today(db)
            except Exception:
                logger.exception("Could not check the last daily risk run")
                due = False
            finally:
                db.close()
            if due:
                run_with_lock(session_factory)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
