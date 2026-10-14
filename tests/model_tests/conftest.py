import itertools
import os
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from models._enums import (
    AlertChannel,
    AlertSeverity,
    GeologyClass,
    ReviewDecision,
    RiskLevel,
)
from models._types import utcnow
from models.emergency_alerts import EmergencyAlert
from models.incident_reports import IncidentReport
from models.landslide_inventory import LandslideInventory
from models.model_versions import ModelVersion
from models.prediction_features import PredictionFeature
from models.rainfall_matrices import RainfallMatrix
from models.risk_inferences import RiskInference
from models.risk_reviews import RiskReview
from models.sectors import Sector
from models.system_audit_logs import SystemAuditLog
from models.users import User
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


@pytest.fixture
def make_sector():

    def _factory(**overrides):
        n = _n()
        defaults = {
            "province_name": "Western",
            "district_name": f"District {n}",
            "sector_name": f"Sector {n}",
            "boundary_ref": f"boundaries/sector_{n}.geojson",
            "mean_slope_deg": Decimal("23.50"),
            "geology_class": GeologyClass.GRANITE,
            "soil_features": {"texture": "clay loam", "depth_cm": 120},
            "land_cover_class": "Cropland",
        }
        return Sector(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_user():

    def _factory(**overrides):
        n = _n()
        defaults = {
            "full_name": f"Test User {n}",
            "email": f"user{n}@example.com",
            "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
            "phone": None,
            "mfa_enrolled": False,
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        return User(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_rainfall():

    def _factory(sector, **overrides):
        defaults = {"sector": sector, "observation_date": date(2026, 4, 1)}
        return RainfallMatrix(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_landslide():

    def _factory(sector, **overrides):
        defaults = {
            "sector": sector,
            "event_date": date(2023, 5, 3),
            "source_name": "RNRA inventory",
        }
        return LandslideInventory(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_model_version():

    def _factory(**overrides):
        n = _n()
        defaults = {
            "model_name": f"landslide-rf-{n}",
            "version_code": "v1.0.0",
            "model_type": "RandomForest",
            "model_path": f"models/landslide_rf_{n}.joblib",
        }
        return ModelVersion(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_inference():

    def _factory(sector, **overrides):
        defaults = {
            "sector": sector,
            "risk_level": RiskLevel.HIGH,
            "risk_score": Decimal("0.78000"),
        }
        return RiskInference(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_feature_snapshot():

    def _factory(inference, **overrides):
        defaults = {
            "inference": inference,
            "historical_features": {"rain_7day": 84.2, "slope": 23.5},
        }
        return PredictionFeature(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_alert():

    def _factory(inference, **overrides):
        defaults = {
            "inference": inference,
            "sector": inference.sector,
            "alert_message": "High landslide risk forecast for the next 24 hours.",
            "severity": AlertSeverity.HIGH,
            "channel": AlertChannel.SMS,
        }
        return EmergencyAlert(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_review():

    def _factory(reviewer, **overrides):
        defaults = {"reviewed_by_user": reviewer, "decision": ReviewDecision.APPROVED}
        return RiskReview(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_incident():

    def _factory(sector, **overrides):
        defaults = {
            "sector": sector,
            "event_date": date(2026, 4, 2),
            "description": "Slope failure blocked the road above the market.",
        }
        return IncidentReport(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def make_audit_log():

    def _factory(**overrides):
        defaults = {"action_type": "LOGIN", "entity_type": "USER"}
        return SystemAuditLog(**{**defaults, **overrides})

    return _factory


@pytest.fixture
def assert_recent_utc():

    def _check(value, seconds=10):
        assert value.tzinfo is not None
        assert abs(utcnow() - value) < timedelta(seconds=seconds)

    return _check
