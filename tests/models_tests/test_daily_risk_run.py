from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from models._enums import ModelStatus
from models.emergency_alerts import EmergencyAlert
from models.risk_inferences import RiskInference
from services.model_version_service import ModelVersionService
from services.risk_run import run_daily_risk

MODEL_FILE = str(Path(__file__).resolve().parents[2] / "assets" / "model_v1.pkl")


@pytest.fixture
def setup(db_session, make_sector, make_rainfall, make_model_version):
    model = make_model_version(model_path=MODEL_FILE, model_status=ModelStatus.DEPLOYED)
    wet = make_sector(sector_name="Wet")
    dry = make_sector(sector_name="Dry")
    empty = make_sector(sector_name="No rain yet")
    db_session.add_all([model, wet, dry, empty])
    day = datetime(2026, 10, 27, tzinfo=timezone.utc)
    for sector in (wet, dry):
        for offset in (1, 0):
            db_session.add(
                make_rainfall(
                    sector,
                    observation_time=day - timedelta(days=offset),
                    rain_1day_mm=Decimal("5"),
                    rain_3day_mm=Decimal("12"),
                    rain_7day_mm=Decimal("30"),
                    rain_10day_mm=Decimal("40"),
                    rain_30day_mm=Decimal("120"),
                )
            )
    db_session.commit()
    return {"model": model, "wet": wet, "dry": dry}


def test_predicts_every_sector_with_rainfall(db_session, setup):
    summary = run_daily_risk(db_session, sync=False)
    assert summary["predictions"] == 2
    assert summary["sectors_without_rainfall"] == 1
    assert summary["failed"] == []
    assert db_session.query(RiskInference).count() == 2


def test_high_and_extreme_become_alerts(db_session, setup, monkeypatch):
    scores = {setup["wet"].sector_id: 0.82, setup["dry"].sector_id: 0.1}
    real = ModelVersionService._build_feature_row

    def fake_prediction(self, model_version_id, feature_matrix):
        return self._current_score

    def remember_sector(self, model, sector, latest_obs):
        self._current_score = scores[sector.sector_id]
        return real(self, model, sector, latest_obs)

    monkeypatch.setattr(ModelVersionService, "calculate_prediction", fake_prediction)
    monkeypatch.setattr(ModelVersionService, "_build_feature_row", remember_sector)

    summary = run_daily_risk(db_session, sync=False)
    assert summary["risk_levels"]["EXTREME"] == 1
    assert summary["risk_levels"]["LOW"] == 1
    assert summary["alerts_created"] == 1
    alert = db_session.query(EmergencyAlert).one()
    assert alert.sector_id == setup["wet"].sector_id


def test_second_run_on_the_same_day_does_not_repeat(db_session, setup):
    run_daily_risk(db_session, sync=False)
    again = run_daily_risk(db_session, sync=False)
    assert again["predictions"] == 0
    assert again["sectors_already_predicted_today"] == 2
    assert db_session.query(RiskInference).count() == 2


def test_runs_the_rainfall_sync_first(db_session, setup):
    class FakeRainfall:
        def run_sync(self, db):
            return {"sectors_synced": 3}

    summary = run_daily_risk(db_session, rainfall=FakeRainfall())
    assert summary["rainfall"] == {"sectors_synced": 3}
    assert summary["predictions"] == 2


def test_uses_the_latest_rainfall_day(db_session, setup):
    run_daily_risk(db_session, sync=False)
    inference = db_session.query(RiskInference).first()
    observed = inference.feature_snapshot.historical_features["rainfall_observations"][
        0
    ]
    assert observed["observation_time"].startswith("2026-10-27")


def test_fails_clearly_without_a_model(db_session, make_sector):
    db_session.add(make_sector())
    db_session.commit()
    with pytest.raises(LookupError):
        run_daily_risk(db_session, sync=False)
