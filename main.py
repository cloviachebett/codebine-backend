from fastapi import FastAPI
from routers.risk_inferences_router import router as risk_inferences_router
from database import create_tables

app = FastAPI(title="TerraWatch", version="0.1.0")

app.include_router(risk_inferences_router)


@app.on_event("startup")
async def startup():
    if hasattr(create_tables, "__await__"):
        await create_tables()
    else:
        create_tables()


@app.get("/health")
def health() -> dict[str, str]:
    """Let deployment verification confirm that the API is responding."""
    return {"status": "ok"}
