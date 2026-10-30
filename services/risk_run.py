import logging
import os
import threading
import uuid
from datetime import datetime, time, timezone
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models._enums import ModelStatus, RiskLevel
from models.model_versions import ModelVersion
from models.rainfall_matrices import RainfallMatrix
from models.risk_inferences import RiskInference
from models.sectors import Sector
from models.system_audit_logs import SystemAuditLog
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


def pick_model(db: Session) -> ModelVersion:
    wanted = os.getenv("RISK_MODEL_VERSION_ID")
    if wanted:
        model = db.get(ModelVersion, uuid.UUID(wanted))
        if model is None:
            raise LookupError(f"RISK_MODEL_VERSION_ID {wanted} was not found")
        return model
    for model_status in (
        ModelStatus.DEPLOYED,
        ModelStatus.READY,
        ModelStatus.TRAINING,
    ):
        model = (
            db.query(ModelVersion)
            .filter(ModelVersion.model_status == model_status)
            .order_by(ModelVersion.created_at.desc())
            .first()
        )
        if model is not None:
            return model
    raise LookupError("No model version is registered")


def latest_rainfall(db: Session) -> dict[uuid.UUID, RainfallMatrix]:
    newest = (
        db.query(
            RainfallMatrix.sector_id,
            func.max(RainfallMatrix.observation_time).label("latest"),
        )
        .group_by(RainfallMatrix.sector_id)
        .subquery()
    )
    rows = (
        db.query(RainfallMatrix)
        .join(
            newest,
            (RainfallMatrix.sector_id == newest.c.sector_id)
            & (RainfallMatrix.observation_time == newest.c.latest),
        )
        .all()
    )
    return {row.sector_id: row for row in rows}


def _observation(row: RainfallMatrix) -> dict[str, Any]:
    observed = row.observation_time
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return {
        "observation_time": observed.isoformat(),
        **{name: float(getattr(row, name)) for name in WINDOWS},
    }


def _predicted_today(db: Session, model_id: uuid.UUID) -> set[uuid.UUID]:
    rows = (
        db.query(RiskInference.sector_id)
        .filter(
            RiskInference.model_version_id == model_id,
            RiskInference.prediction_time >= _start_of_today(),
        )
        .all()
    )
    return {sector_id for (sector_id,) in rows}


def _sync_rainfall(db: Session, rainfall) -> dict[str, Any]:
    try:
        return (rainfall or rainfall_service).run_sync(db)
    except Exception as exc:
        db.rollback()
        logger.warning("Rainfall sync failed, using stored rainfall: %s", exc)
        return {"error": str(exc)}


def run_daily_risk(db: Session, sync: bool = True, rainfall=None) -> dict[str, Any]:
    summary: dict[str, Any] = {"started_at": datetime.now(timezone.utc).isoformat()}
    if sync:
        summary["rainfall"] = _sync_rainfall(db, rainfall)

    model = pick_model(db)
    rain = latest_rainfall(db)
    done_today = _predicted_today(db, model.model_version_id)
    predictor = ModelVersionService(db)

    levels = {level.value: 0 for level in RiskLevel}
    alerts_created = 0
    skipped_no_rainfall = 0
    skipped_already_done = 0
    failed: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []

    for sector in db.query(Sector).order_by(Sector.district_name, Sector.sector_name):
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
            db.rollback()
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
    db.add(
        SystemAuditLog(
            action_type=RUN_OK,
            entity_type="risk_inferences",
            entity_id=str(model.model_version_id),
            execution_details=summary,
        )
    )
    db.commit()
    return summary


def ran_today(db: Session) -> bool:
    return (
        db.query(SystemAuditLog.log_id)
        .filter(
            SystemAuditLog.action_type == RUN_OK,
            SystemAuditLog.created_at >= _start_of_today(),
        )
        .first()
        is not None
    )


def last_run(db: Session) -> SystemAuditLog | None:
    return (
        db.query(SystemAuditLog)
        .filter(SystemAuditLog.action_type.in_([RUN_OK, RUN_FAILED]))
        .order_by(SystemAuditLog.created_at.desc())
        .first()
    )


def is_running() -> bool:
    return _running.locked()


def _record_failure(session_factory: Callable[[], Session], error: Exception) -> None:
    db = session_factory()
    try:
        db.add(
            SystemAuditLog(
                action_type=RUN_FAILED,
                entity_type="risk_inferences",
                execution_details={"error": str(error)},
            )
        )
        db.commit()
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


def start_in_background(session_factory: Callable[[], Session]) -> bool:
    if not _running.acquire(blocking=False):
        return False
    threading.Thread(
        target=_run_and_release, args=(session_factory,), daemon=True
    ).start()
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
