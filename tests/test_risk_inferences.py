import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_dependency import require_admin
from database import Base, get_db
from main import app
from models._enums import GeologyClass, ModelStatus, UserRole
from models.model_versions import ModelVersion
from models.sectors import Sector

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _signed_in_as_admin():
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(
        role=UserRole.ADMIN
    )
    yield
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


MODEL_VERSION_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
SECTOR_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


@pytest.fixture
def seeded_db(db_session):
    sector = Sector(
        sector_id=uuid.UUID(SECTOR_ID),
        province_name="Western",
        district_name="Rutsiro",
        sector_name="Boneza",
        boundary_ref="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        mean_slope_deg=15.5,
        geology_class=GeologyClass.ALLUVIUM,
        soil_features={"clay": 0.3},
        land_cover_class="forest",
    )
    mv = ModelVersion(
        model_version_id=uuid.UUID(MODEL_VERSION_ID),
        model_name="landslide_risk_model",
        version_code="v1.0.0",
        model_type="random_forest",
        model_path="/models/x.pkl",
        precision={"o": 0.85},
        recall={"o": 0.82},
        f1_score={"o": 0.83},
        model_status=ModelStatus.DEPLOYED,
    )
    db_session.add_all([sector, mv])
    db_session.commit()
    return db_session


def test_risk_inference_workflow(client, seeded_db):
    payload = {
        "sector_id": SECTOR_ID,
        "model_version_id": MODEL_VERSION_ID,
        "risk_level": "HIGH",
        "risk_score": 0.85432,
    }

    response = client.post("/analytics/inferences", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["risk_level"] == "HIGH"

    inference_id = data["inference_id"]
    get_res = client.get(f"/analytics/inferences/{inference_id}")
    assert get_res.status_code == 200
    assert float(get_res.json()["risk_score"]) == 0.85432
