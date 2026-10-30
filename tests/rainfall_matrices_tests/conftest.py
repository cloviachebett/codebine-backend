import itertools
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from auth_dependency import require_admin
from models._enums import GeologyClass, UserRole
from models.dataset_metadata import DatasetMetadata
from models.rainfall_matrices import RainfallMatrix
from models.sectors import Sector
from database import Base, get_db
from main import app
from services.chirps_gee import SectorArea  # noqa: F401
from services.rainfall_math import iter_days
import services.rainfall_matrices as rainfall_module

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


@pytest.fixture(autouse=True)
def _chirps_environment(monkeypatch):
    """CHIRPS/GEE settings are read straight from the environment now
    (see services/chirps_gee.py), so the test env is pinned here."""
    monkeypatch.setenv("CHIRPS_ID", "TEST/COLLECTION")
    monkeypatch.setenv("CHIRPS_SCALE_M", "5566")
    monkeypatch.setenv("GEE_MAX_FEATURES_PER_REQUEST", "4000")
    monkeypatch.setenv("GEE_PROJECT", "")
    monkeypatch.setenv("GEE_PRIVATE_KEY_PATH", "")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "")


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


_counter = itertools.count(1)


def _n():
    return next(_counter)


def square(lon: float, lat: float, size: float = 0.1) -> dict:
    ring = [
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture
def make_sector():
    def _factory(**overrides):
        n = _n()
        defaults = {
            "province_name": "Western",
            "district_name": f"District {n}",
            "sector_name": f"Sector {n}",
            "boundary_ref": json.dumps(square(29.0 + n * 0.2, -2.0)),
            "mean_slope_deg": Decimal("23.50"),
            "geology_class": GeologyClass.GRANITE,
            "soil_features": {"texture": "clay loam", "depth_cm": 120},
            "land_cover_class": "Cropland",
        }
        return Sector(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def add_sector(db_session, make_sector):
    def _add(**overrides):
        sector = make_sector(**overrides)
        db_session.add(sector)
        db_session.commit()
        db_session.refresh(sector)
        return sector

    return _add


@pytest.fixture
def make_dataset():
    def _factory(**overrides):
        n = _n()
        defaults = {
            "dataset_name": f"CHIRPS rainfall {n}",
            "factor_type": "RAINFALL",
            "source_name": "CHIRPS",
            "file_path": f"datasets/chirps_{n}.tif",
            "version": "v1",
        }
        return DatasetMetadata(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_rainfall():
    def _factory(sector, **overrides):
        defaults = {
            "sector": sector,
            "observation_time": datetime(2026, 4, 1, tzinfo=timezone.utc),
        }
        return RainfallMatrix(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def rainfall_settings(monkeypatch):
    """Settings for the rainfall service in tests (never touches .env)."""
    settings = SimpleNamespace(
        chirps_collection="TEST/COLLECTION",
        boundary_sector_property="ADM3_EN",
        boundary_district_property="ADM2_EN",
        rainfall_sync_lookback_days=3,
    )
    # The router talks to a module-level singleton; keep it on the test settings.
    monkeypatch.setattr(rainfall_module.rainfall_service, "settings", settings)
    return settings


SPIKE = date(2024, 3, 10)


class FakeChirps:
    """Stands in for CHIRPSGEEService: spike_mm on SPIKE, 0 mm on every other day."""

    def __init__(self, latest=date(2024, 3, 31), fail=False, missing=(), spike_mm=50.0):
        self.latest = latest
        self.fail = fail
        self.missing = set(missing)
        self.spike_mm = spike_mm
        self.unresolved = []
        self.calls = []

    def latest_available_date(self):
        return self.latest

    def fetch_daily_rainfall(self, areas, start, end):
        self.calls.append({"start": start, "end": end, "areas": list(areas)})
        if self.fail:
            raise RuntimeError("Earth Engine is down")
        return {
            a.sector_id: {
                d: (self.spike_mm if d == SPIKE else 0.0)
                for d in iter_days(start, end)
                if d not in self.missing
            }
            for a in areas
        }


@pytest.fixture
def fake_chirps():
    return FakeChirps
