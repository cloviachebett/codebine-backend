import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from database import SessionLocal
from routers.rainfall_matrices import router as rainfall_router
from services.scheduler import rainfall_sync_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = None
    if settings.rainfall_sync_enabled:
        task = asyncio.create_task(
            rainfall_sync_loop(settings, SessionLocal, stop_event)
        )
    yield
    stop_event.set()
    if task is not None:
        await task


app = FastAPI(title="TerraWatch", version="0.1.0", lifespan=lifespan)

app.include_router(rainfall_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
