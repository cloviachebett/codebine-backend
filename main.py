from fastapi import FastAPI
from routers.prediction_features_router import router as prediction_features_router

app = FastAPI(title="TerraWatch", version="0.1.0")

app.include_router(prediction_features_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
