from types import SimpleNamespace
from uuid import uuid4

import pytest

from auth_dependency import require_admin
from main import app

from models._enums import AlertStatus, RiskLevel, UserRole
from models.emergency_alerts import EmergencyAlert
from models.system_audit_logs import SystemAuditLog

URL = "/api/v1/alerts"


@pytest.fixture(autouse=True)
def _signed_in_as_admin():
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(
        role=UserRole.ADMIN
    )
    yield
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def sector(db_session, make_sector):
    item = make_sector(district_name="Rubavu", sector_name="Gisenyi")
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def save_inference(db_session, make_inference, sector):
    def _save(risk_level):
        inference = make_inference(sector, risk_level=risk_level)
        db_session.add(inference)
        db_session.commit()
        return inference

    return _save


def count_alerts(db_session):
    db_session.expire_all()
    return db_session.query(EmergencyAlert).count()


@pytest.mark.parametrize(
    "risk_level, severity",
    [(RiskLevel.HIGH, "HIGH"), (RiskLevel.EXTREME, "CRITICAL")],
)
def test_high_or_extreme_prediction_creates_a_pending_alert(
    client, db_session, save_inference, risk_level, severity
):
    inference = save_inference(risk_level)

    response = client.post(URL, json={"inference_id": str(inference.inference_id)})

    assert response.status_code == 201
    data = response.json()
    assert data["inference_id"] == str(inference.inference_id)
    assert data["sector_id"] == str(inference.sector_id)
    assert data["district_name"] == "Rubavu"
    assert data["sector_name"] == "Gisenyi"
    assert data["risk_level"] == risk_level.value
    assert data["severity"] == severity
    assert data["alert_status"] == "PENDING_REVIEW"
    assert "Gisenyi" in data["alert_message"]
    assert "channel" not in data
    assert count_alerts(db_session) == 1


def test_create_writes_an_audit_entry(client, db_session, save_inference):
    inference = save_inference(RiskLevel.HIGH)
    alert_id = client.post(
        URL, json={"inference_id": str(inference.inference_id)}
    ).json()["alert_id"]

    logs = db_session.query(SystemAuditLog).all()
    assert len(logs) == 1
    assert logs[0].action_type == "EMERGENCY_ALERT_CREATED"
    assert logs[0].entity_id == alert_id


@pytest.mark.parametrize("risk_level", [RiskLevel.LOW, RiskLevel.MODERATE])
def test_low_or_moderate_prediction_is_not_flagged(
    client, db_session, save_inference, risk_level
):
    inference = save_inference(risk_level)
    response = client.post(URL, json={"inference_id": str(inference.inference_id)})
    assert response.status_code == 422
    assert count_alerts(db_session) == 0


def test_second_alert_for_same_prediction_is_refused(
    client, db_session, save_inference
):
    inference = save_inference(RiskLevel.EXTREME)
    body = {"inference_id": str(inference.inference_id)}
    assert client.post(URL, json=body).status_code == 201
    assert client.post(URL, json=body).status_code == 409
    assert count_alerts(db_session) == 1


def test_unknown_prediction_returns_404(client, db_session):
    response = client.post(URL, json={"inference_id": str(uuid4())})
    assert response.status_code == 404
    assert count_alerts(db_session) == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"inference_id": "not-a-uuid"},
        {"inference_id": str(uuid4()), "severity": "LOW"},
        {"inference_id": str(uuid4()), "channel": "SMS"},
    ],
)
def test_invalid_body_is_rejected(client, db_session, body):
    assert client.post(URL, json=body).status_code == 422
    assert count_alerts(db_session) == 0


def test_list_returns_newest_first_and_filters_by_status(
    client, db_session, save_inference
):
    first = save_inference(RiskLevel.HIGH)
    second = save_inference(RiskLevel.EXTREME)
    client.post(URL, json={"inference_id": str(first.inference_id)})
    client.post(URL, json={"inference_id": str(second.inference_id)})
    alert = (
        db_session.query(EmergencyAlert)
        .filter_by(inference_id=first.inference_id)
        .one()
    )
    alert.alert_status = AlertStatus.APPROVED
    db_session.commit()

    everything = client.get(URL).json()
    pending = client.get(URL, params={"alert_status": "PENDING_REVIEW"}).json()

    assert [a["inference_id"] for a in everything] == [
        str(second.inference_id),
        str(first.inference_id),
    ]
    assert [a["inference_id"] for a in pending] == [str(second.inference_id)]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"offset": -1}, {"alert_status": "PENDING"}]
)
def test_list_rejects_invalid_query(client, params):
    assert client.get(URL, params=params).status_code == 422


def test_get_one_and_unknown_id(client, save_inference):
    inference = save_inference(RiskLevel.HIGH)
    alert_id = client.post(
        URL, json={"inference_id": str(inference.inference_id)}
    ).json()["alert_id"]

    assert client.get(f"{URL}/{alert_id}").json()["alert_id"] == alert_id
    assert client.get(f"{URL}/{uuid4()}").status_code == 404
    assert client.get(f"{URL}/not-a-uuid").status_code == 422
