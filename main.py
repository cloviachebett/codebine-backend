from fastapi import FastAPI
from routers.risk_inferences_router import router as risk_inferences_router

from routers.incidents import router as incidents_router
from routers.alerts import router as alerts_router
from routers.reviews import router as reviews_router

app = FastAPI(title="TerraWatch", version="0.1.0")
app.include_router(incidents_router)
app.include_router(alerts_router)
app.include_router(reviews_router)

app.include_router(risk_inferences_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
