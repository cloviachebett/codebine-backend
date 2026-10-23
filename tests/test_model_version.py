import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

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


def test_register_and_get_model_version(client):
    payload = {
        "model_name": "landslide_risk_model",
        "version_code": "v1.0.0",
        "model_type": "random_forest",
        "model_path": "/models/landslide_risk_v1.pkl",
        "precision": {"overall": 0.85},
        "recall": {"overall": 0.82},
        "f1_score": {"overall": 0.83},
        "model_status": "DEPLOYED",
    }

    response = client.post("/analytics/models", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["model_name"] == "landslide_risk_model"
    assert data["version_code"] == "v1.0.0"

    get_res = client.get(f"/analytics/models/{data['model_version_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["model_name"] == "landslide_risk_model"


def test_register_duplicate_version_returns_400(client):
    payload = {
        "model_name": "landslide_risk_model",
        "version_code": "v1.0.0",
        "model_type": "random_forest",
        "model_path": "/models/landslide_risk_v1.pkl",
        "precision": {"overall": 0.85},
        "recall": {"overall": 0.82},
        "f1_score": {"overall": 0.83},
        "model_status": "DEPLOYED",
    }
    client.post("/analytics/models", json=payload)

    response = client.post("/analytics/models", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_missing_model_version_returns_404(client):
    response = client.get(f"/analytics/models/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
