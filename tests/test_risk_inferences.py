import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


@pytest.fixture(autouse=True)
async def _fresh_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


MODEL_VERSION_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
SECTOR_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


@pytest.mark.asyncio
async def test_risk_inference_workflow(client):
    payload = {
        "sector_id": SECTOR_ID,
        "model_version_id": MODEL_VERSION_ID,
        "risk_level": "HIGH",
        "risk_score": 0.85432,
    }

    response = await client.post("/analytics/inferences", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["risk_level"] == "HIGH"

    inference_id = data["inference_id"]
    get_res = await client.get(f"/analytics/inferences/{inference_id}")
    assert get_res.status_code == 200
    assert float(get_res.json()["risk_score"]) == 0.85432
