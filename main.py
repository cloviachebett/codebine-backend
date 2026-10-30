import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.alerts import router as alerts_router
from routers.incidents import router as incidents_router
from routers.prediction_features_router import router as prediction_features_router
from routers.reviews import router as reviews_router
from routers.risk_inferences_router import router as risk_inferences_router
from routers.model_versions_router import router as model_versions_router
from routers.rainfall_matrices import router as rainfall_router
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.sectors import router as sectors_router
from routers.system_logs import router as system_logs_router
from database import SessionLocal
from services import risk_run
from services.system_logs import AutomatedAuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = threading.Event()
    if risk_run.auto_run_enabled():
        risk_run.start_auto_runner(SessionLocal, stop)
    yield
    stop.set()


app = FastAPI(title="TerraWatch", version="0.1.0", lifespan=lifespan)

app.add_middleware(AutomatedAuditMiddleware)

DEFAULT_CORS_ORIGINS = "http://localhost:3000,https://codebine-dashboard.vercel.app"
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents_router)
app.include_router(alerts_router)
app.include_router(reviews_router)
app.include_router(sectors_router)
app.include_router(risk_inferences_router)
app.include_router(prediction_features_router)
app.include_router(system_logs_router)
app.include_router(model_versions_router)
app.include_router(rainfall_router)
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
