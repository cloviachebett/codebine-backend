import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models._enums import GeologyClass, ModelStatus
from models.model_versions import ModelVersion
from models.risk_inferences import RiskInference
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


@pytest.fixture
def inference_id(db_session):
    sector = Sector(
        sector_id=uuid.uuid4(),
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
        model_version_id=uuid.uuid4(),
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
    inference = RiskInference(
        inference_id=uuid.uuid4(),
        sector_id=sector.sector_id,
        model_version_id=mv.model_version_id,
        risk_level="HIGH",
        risk_score=0.85432,
    )
    db_session.add(inference)
    db_session.commit()
    db_session.refresh(inference)
    return inference.inference_id


def test_save_and_get_feature_snapshot(client, inference_id):
    payload = {
        "inference_id": str(inference_id),
        "historical_features": {"rain_7day": 84.2, "slope": 23.5},
    }

    response = client.post("/analytics/features", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["inference_id"] == str(inference_id)
    assert data["historical_features"] == {"rain_7day": 84.2, "slope": 23.5}

    get_res = client.get(f"/analytics/features/inference/{inference_id}")
    assert get_res.status_code == 200
    assert float(get_res.json()["historical_features"]["rain_7day"]) == 84.2


def test_duplicate_feature_snapshot_returns_400(client, inference_id):
    payload = {
        "inference_id": str(inference_id),
        "historical_features": {"rain_7day": 84.2},
    }
    client.post("/analytics/features", json=payload)

    response = client.post("/analytics/features", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_missing_feature_returns_404(client, inference_id):
    response = client.get(f"/analytics/features/inference/{inference_id}")
    assert response.status_code == 404
    assert "snapshot" in response.json()["detail"]
