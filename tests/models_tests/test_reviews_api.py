from types import SimpleNamespace
from uuid import uuid4

import pytest

from main import app
from models._enums import AccountStatus, AlertStatus, RiskLevel
from models.emergency_alerts import EmergencyAlert
from models.risk_reviews import RiskReview
from models.system_audit_logs import SystemAuditLog
from services.current_user import get_current_user

URL = "/api/v1/reviews"


@pytest.fixture
def analyst(db_session, make_user):
    user = make_user(full_name="Analyst One")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def logged_in(client, analyst):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=analyst.user_id, account_status=AccountStatus.ACTIVE
    )
    return analyst


@pytest.fixture
def inference(db_session, make_sector, make_inference):
    item = make_inference(make_sector(), risk_level=RiskLevel.HIGH)
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def alert(db_session, inference, make_alert):
    item = make_alert(inference)
    db_session.add(item)
    db_session.commit()
    return item


def count_reviews(db_session):
    db_session.expire_all()
    return db_session.query(RiskReview).count()


def test_review_requires_a_login(client, db_session, alert, monkeypatch):
    monkeypatch.delenv("DEV_USER_ID", raising=False)
    body = {"alert_id": str(alert.alert_id), "decision": "APPROVED"}
    assert client.post(URL, json=body).status_code == 401
    assert count_reviews(db_session) == 0


def test_dev_user_setting_logs_in_an_active_user(
    client, db_session, alert, analyst, monkeypatch
):
    monkeypatch.setenv("DEV_USER_ID", str(analyst.user_id))
    body = {"alert_id": str(alert.alert_id), "decision": "APPROVED"}
    response = client.post(URL, json=body)
    assert response.status_code == 201
    assert response.json()["reviewed_by"] == str(analyst.user_id)


def test_dev_user_setting_rejects_a_suspended_user(
    client, db_session, alert, make_user, monkeypatch
):
    user = make_user(account_status=AccountStatus.SUSPENDED)
    db_session.add(user)
    db_session.commit()
    monkeypatch.setenv("DEV_USER_ID", str(user.user_id))
    body = {"alert_id": str(alert.alert_id), "decision": "APPROVED"}
    assert client.post(URL, json=body).status_code == 401


@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED", "DISMISSED"])
def test_review_of_an_alert_updates_its_status(
    client, db_session, logged_in, alert, decision
):
    body = {
        "alert_id": str(alert.alert_id),
        "decision": decision,
        "comments": "  Confirmed heavy rain in the area.  ",
    }
    response = client.post(URL, json=body)

    assert response.status_code == 201
    data = response.json()
    assert data["alert_id"] == str(alert.alert_id)
    assert data["inference_id"] is None
    assert data["decision"] == decision
    assert data["comments"] == "Confirmed heavy rain in the area."
    assert data["reviewed_by"] == str(logged_in.user_id)
    assert data["reviewer_name"] == "Analyst One"
    db_session.expire_all()
    assert db_session.get(EmergencyAlert, alert.alert_id).alert_status == AlertStatus(
        decision
    )


def test_review_writes_an_audit_entry(client, db_session, logged_in, alert):
    body = {"alert_id": str(alert.alert_id), "decision": "REJECTED"}
    review_id = client.post(URL, json=body).json()["review_id"]

    logs = db_session.query(SystemAuditLog).all()
    assert len(logs) == 1
    assert logs[0].action_type == "RISK_REVIEW_CREATED"
    assert logs[0].user_id == logged_in.user_id
    assert logs[0].entity_id == review_id
    assert logs[0].execution_details == {"decision": "REJECTED"}


def test_alert_cannot_be_reviewed_twice(client, db_session, logged_in, alert):
    body = {"alert_id": str(alert.alert_id), "decision": "APPROVED"}
    assert client.post(URL, json=body).status_code == 201
    body["decision"] = "DISMISSED"
    assert client.post(URL, json=body).status_code == 409
    assert count_reviews(db_session) == 1


def test_prediction_can_be_reviewed_more_than_once(
    client, db_session, logged_in, inference
):
    body = {"inference_id": str(inference.inference_id), "decision": "APPROVED"}
    assert client.post(URL, json=body).status_code == 201
    body["decision"] = "REJECTED"
    assert client.post(URL, json=body).status_code == 201
    assert count_reviews(db_session) == 2


@pytest.mark.parametrize("target", ["alert_id", "inference_id"])
def test_unknown_target_returns_404(client, db_session, logged_in, target):
    body = {target: str(uuid4()), "decision": "APPROVED"}
    assert client.post(URL, json=body).status_code == 404
    assert count_reviews(db_session) == 0


def test_both_or_neither_target_is_rejected(
    client, db_session, logged_in, alert, inference
):
    both = {
        "alert_id": str(alert.alert_id),
        "inference_id": str(inference.inference_id),
        "decision": "APPROVED",
    }
    assert client.post(URL, json=both).status_code == 422
    assert client.post(URL, json={"decision": "APPROVED"}).status_code == 422
    assert count_reviews(db_session) == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"decision": "MAYBE"},
        {"decision": "approved"},
        {"reviewed_by": str(uuid4())},
        {"reviewed_at": "2020-01-01T00:00:00Z"},
        {"comments": "x" * 2001},
    ],
)
def test_invalid_body_is_rejected(client, db_session, logged_in, alert, extra):
    body = {"alert_id": str(alert.alert_id), "decision": "APPROVED", **extra}
    assert client.post(URL, json=body).status_code == 422
    assert count_reviews(db_session) == 0


def test_list_returns_newest_first_and_filters(
    client, db_session, logged_in, alert, inference
):
    client.post(
        URL, json={"inference_id": str(inference.inference_id), "decision": "APPROVED"}
    )
    client.post(URL, json={"alert_id": str(alert.alert_id), "decision": "DISMISSED"})

    everything = client.get(URL).json()
    for_alert = client.get(URL, params={"alert_id": str(alert.alert_id)}).json()

    assert [r["decision"] for r in everything] == ["DISMISSED", "APPROVED"]
    assert [r["decision"] for r in for_alert] == ["DISMISSED"]
    assert everything[0]["reviewer_name"] == "Analyst One"
