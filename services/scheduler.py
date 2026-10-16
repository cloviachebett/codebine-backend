import asyncio
import logging
from typing import Any, Callable

from services.rainfall_matrices import RainfallService

logger = logging.getLogger(__name__)


def run_rainfall_sync(
    session_factory: Callable[[], Any], settings=None, **kwargs
) -> dict:
    """One sync run in its own DB session (used by the scheduler and scripts/sync_rainfall.py)."""
    db = session_factory()
    try:
        return RainfallService(settings=settings).run_sync(db, **kwargs)
    finally:
        db.close()


async def rainfall_sync_loop(
    settings, session_factory, stop_event: asyncio.Event
) -> None:
    # Refresh rainfall every ``rainfall_sync_interval_hours`` until ``stop_event`` is set.

    # A failed run is logged with its traceback and retried next interval; the loop itself must not die, otherwise rainfall silently stops updating.

    interval = settings.rainfall_sync_interval_hours * 3600
    while not stop_event.is_set():
        try:
            summary = await asyncio.to_thread(
                run_rainfall_sync, session_factory, settings
            )
            logger.info("Rainfall sync finished: %s", summary)
        except Exception:  # supervisor loop: log and keep running
            logger.exception("Scheduled rainfall sync failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
