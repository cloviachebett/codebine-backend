import json
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from auth_dependency import require_admin
from main import app
from models._enums import GeologyClass, ModelStatus, RiskLevel, UserRole
from models.risk_inferences import RiskInference
from models.system_audit_logs import SystemAuditLog
from routers.risk_runs import get_session_factory
from services import risk_run, storage
from services.current_user import get_current_user as signed_in_user
from services.model_version_service import ModelVersionService
from services.rainfall_matrices import RainfallService

MODEL_FILE = str(Path(__file__).resolve().parents[2] / "assets" / "model_v1.pkl")
ADMIN = SimpleNamespace(role=UserRole.ADMIN)


@pytest.fixture
def TestingSessionLocal(db_session):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())


@pytest.fixture
def as_admin():
    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[signed_in_user] = lambda: ADMIN
    yield
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(signed_in_user, None)


@pytest.fixture
def world(db_session, make_sector, make_rainfall, make_model_version):
    model = make_model_version(model_path=MODEL_FILE, model_status=ModelStatus.DEPLOYED)
    sectors = [
        make_sector(district_name="Karongi", sector_name="Gitesi"),
        make_sector(district_name="Rubavu", sector_name="Gisenyi"),
    ]
    db_session.add_all([model, *sectors])
    for sector in sectors:
        db_session.add(
            make_rainfall(
                sector,
                observation_time=datetime(2026, 10, 27, tzinfo=timezone.utc),
                rain_1day_mm=Decimal("4"),
                rain_3day_mm=Decimal("10"),
                rain_7day_mm=Decimal("25"),
                rain_10day_mm=Decimal("33"),
                rain_30day_mm=Decimal("90"),
            )
        )
    db_session.commit()
    return {"model": model, "sectors": sectors}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/alerts",
        "/api/v1/rainfall/sync",
        "/analytics/models",
        "/analytics/inferences",
        "/api/v1/risk-runs",
    ],
)
def test_write_endpoints_need_an_admin(client, path):
    assert client.post(path, json={}).status_code in (401, 403)


@pytest.mark.parametrize(
    "path",
    ["/analytics/inferences", "/api/v1/risk-runs/latest", "/analytics/models/active"],
)
def test_new_read_endpoints_need_login(client, path):
    assert client.get(path).status_code == 401


def test_run_now_from_the_dashboard(
    client, db_session, world, as_admin, monkeypatch, TestingSessionLocal
):
    monkeypatch.setattr(RainfallService, "run_sync", lambda self, db: {"ok": True})
    app.dependency_overrides[get_session_factory] = lambda: TestingSessionLocal
    started = client.post("/api/v1/risk-runs")
    assert started.status_code == 202
    deadline = time.monotonic() + 30
    while risk_run.is_running() and time.monotonic() < deadline:
        time.sleep(0.05)
    latest = client.get("/api/v1/risk-runs/latest").json()
    assert latest["running"] is False
    assert latest["last_run"]["status"] == "OK"
    assert latest["last_run"]["details"]["predictions"] == 2


def test_run_now_refuses_a_second_run(client, as_admin):
    assert risk_run._running.acquire(blocking=False)
    try:
        assert client.post("/api/v1/risk-runs").status_code == 409
    finally:
        risk_run._running.release()


def test_failed_run_is_recorded(db_session, world, monkeypatch, TestingSessionLocal):
    def broken(db, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(risk_run, "run_daily_risk", broken)
    assert risk_run.run_with_lock(TestingSessionLocal) is True
    last = risk_run.last_run(db_session)
    assert last.action_type == risk_run.RUN_FAILED
    assert "database went away" in last.execution_details["error"]


def test_rainfall_failure_still_predicts_from_stored_rainfall(db_session, world):
    class Down:
        def run_sync(self, db):
            raise RuntimeError("Earth Engine unavailable")

    summary = risk_run.run_daily_risk(db_session, rainfall=Down())
    assert "Earth Engine unavailable" in summary["rainfall"]["error"]
    assert summary["predictions"] == 2


def test_auto_runner_runs_once_when_due(world, monkeypatch, TestingSessionLocal):
    calls = []
    monkeypatch.setattr(
        risk_run, "run_with_lock", lambda factory: calls.append(1) or True
    )
    stop = threading.Event()
    thread = risk_run.start_auto_runner(
        TestingSessionLocal, stop, first_check_seconds=0.01, check_every_seconds=0.01
    )
    while not calls:
        thread.join(timeout=0.05)
    stop.set()
    thread.join(timeout=1)
    assert calls


def test_auto_runner_waits_when_already_ran_today(
    db_session, world, monkeypatch, TestingSessionLocal
):
    db_session.add(
        SystemAuditLog(action_type=risk_run.RUN_OK, entity_type="risk_inferences")
    )
    db_session.commit()
    calls = []
    monkeypatch.setattr(risk_run, "run_with_lock", lambda factory: calls.append(1))
    stop = threading.Event()
    thread = risk_run.start_auto_runner(
        TestingSessionLocal, stop, first_check_seconds=0.01, check_every_seconds=0.01
    )
    thread.join(timeout=0.2)
    stop.set()
    thread.join(timeout=1)
    assert calls == []


def test_auto_run_is_off_unless_switched_on(monkeypatch):
    monkeypatch.delenv("DAILY_RISK_RUN", raising=False)
    assert risk_run.auto_run_enabled() is False
    monkeypatch.setenv("DAILY_RISK_RUN", "true")
    assert risk_run.auto_run_enabled() is True


def test_predictions_list_for_the_map(
    client, db_session, world, as_admin, make_inference
):
    gitesi, gisenyi = world["sectors"]
    old = make_inference(
        gitesi,
        model_version=world["model"],
        risk_level=RiskLevel.LOW,
        risk_score=Decimal("0.1"),
        prediction_time=datetime.now(timezone.utc) - timedelta(days=1),
    )
    new = make_inference(
        gitesi,
        model_version=world["model"],
        risk_level=RiskLevel.EXTREME,
        risk_score=Decimal("0.9"),
    )
    other = make_inference(
        gisenyi,
        model_version=world["model"],
        risk_level=RiskLevel.MODERATE,
        risk_score=Decimal("0.3"),
    )
    db_session.add_all([old, new, other])
    db_session.commit()

    everything = client.get("/analytics/inferences").json()
    assert len(everything) == 3
    assert everything[0]["sector_name"] in {"Gitesi", "Gisenyi"}

    latest = client.get("/analytics/inferences", params={"latest_only": True}).json()
    assert {(row["sector_name"], row["risk_level"]) for row in latest} == {
        ("Gitesi", "EXTREME"),
        ("Gisenyi", "MODERATE"),
    }

    karongi = client.get("/analytics/inferences", params={"district": "Karongi"}).json()
    assert {row["district_name"] for row in karongi} == {"Karongi"}

    extreme = client.get(
        "/analytics/inferences", params={"risk_level": "extreme"}
    ).json()
    assert [row["risk_level"] for row in extreme] == ["EXTREME"]

    assert (
        client.get("/analytics/inferences", params={"risk_level": "huge"}).status_code
        == 422
    )


def test_active_model(client, world, as_admin):
    response = client.get("/analytics/models/active")
    assert response.status_code == 200
    assert response.json()["model_version_id"] == str(world["model"].model_version_id)


def test_active_model_missing(client, as_admin):
    assert client.get("/analytics/models/active").status_code == 404


def test_prediction_keeps_the_exact_model_inputs(db_session, world):
    risk_run.run_daily_risk(db_session, sync=False)
    inference = db_session.query(RiskInference).first()
    inputs = inference.feature_snapshot.historical_features["model_inputs"]
    assert set(inputs) == {
        "month",
        "rain_1day_mm",
        "rain_3day_mm",
        "rain_7day_mm",
        "rain_10day_mm",
        "rain_30day_mm",
        "mean_slope_deg",
        "land_cover_class",
    }
    assert inputs["month"] == 10
    assert inputs["rain_30day_mm"] == 90.0


def test_a_retrained_model_can_use_geology_and_soil(make_sector):
    sector = make_sector(
        geology_class=GeologyClass.GRANITE,
        soil_features={"texture": "clay loam", "depth_cm": 120},
        mean_slope_deg=Decimal("30.5"),
    )
    model = SimpleNamespace(
        feature_names_in_=[
            "geology_class",
            "soil_texture",
            "depth_cm",
            "mean_slope_deg",
            "rain_7day_mm",
        ]
    )
    row = ModelVersionService(None)._build_feature_row(
        model,
        sector,
        {"rain_7day_mm": 25.0, "observation_time": "2026-10-27T00:00:00+00:00"},
    )
    assert row == ["GRANITE", "clay loam", 120, 30.5, 25.0]


class FakeS3:
    def __init__(self):
        self.saved = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.saved[(Bucket, Key)] = json.loads(Body)

    def download_file(self, bucket, key, local):
        Path(local).write_bytes(Path(MODEL_FILE).read_bytes())


def test_daily_run_is_saved_to_s3(db_session, world, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "_client", lambda: fake)
    monkeypatch.setenv("S3_BUCKET", "terrawatch-data")
    summary = risk_run.run_daily_risk(db_session, sync=False)
    assert summary["archive"].startswith("s3://terrawatch-data/daily-runs/")
    (saved,) = fake.saved.values()
    assert len(saved["sectors"]) == 2
    assert {"risk_level", "rain_30day_mm", "sector_name"} <= set(saved["sectors"][0])


def test_no_bucket_means_nothing_is_uploaded(db_session, world, monkeypatch):
    monkeypatch.delenv("S3_BUCKET", raising=False)
    summary = risk_run.run_daily_risk(db_session, sync=False)
    assert summary["archive"] is None


def test_model_can_be_loaded_from_s3(db_session, world, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "_client", lambda: FakeS3())
    monkeypatch.setattr(storage.tempfile, "gettempdir", lambda: str(tmp_path))
    world["model"].model_path = "s3://terrawatch-models/model_v2.pkl"
    db_session.commit()
    summary = risk_run.run_daily_risk(db_session, sync=False)
    assert summary["predictions"] == 2
    assert (
        tmp_path / "terrawatch-models" / "terrawatch-models" / "model_v2.pkl"
    ).exists()
