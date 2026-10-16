from fastapi import FastAPI

from routers.incidents import router as incidents_router

app = FastAPI(title="TerraWatch", version="0.1.0")
app.include_router(incidents_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
