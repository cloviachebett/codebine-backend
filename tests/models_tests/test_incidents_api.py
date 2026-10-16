from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from models.incident_reports import IncidentReport
from models.system_audit_logs import SystemAuditLog

URL = "/api/v1/incidents"


@pytest.fixture
def sector(db_session, make_sector):
    item = make_sector(district_name="Ngororero", sector_name="Bwira")
    db_session.add(item)
    db_session.commit()
    return item


def body(sector, **overrides):
    data = {
        "sector_id": str(sector.sector_id),
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "description": "Minor landslide blocking secondary access paths.",
    }
    data.update(overrides)
    return data


def count_reports(db_session):
    db_session.expire_all()
    return db_session.query(IncidentReport).count()


def test_create_returns_the_saved_report(client, sector, db_session):
    response = client.post(URL, json=body(sector))

    assert response.status_code == 201
    data = response.json()
    assert data["sector_id"] == str(sector.sector_id)
    assert data["district_name"] == "Ngororero"
    assert data["sector_name"] == "Bwira"
    assert data["description"] == "Minor landslide blocking secondary access paths."
    assert data["reported_by"] is None
    assert "status" not in data
    reported_at = datetime.fromisoformat(data["reported_at"])
    assert abs(datetime.now(timezone.utc) - reported_at) < timedelta(minutes=1)
    assert count_reports(db_session) == 1


def test_create_writes_an_audit_entry(client, sector, db_session):
    report_id = client.post(URL, json=body(sector)).json()["report_id"]

    logs = db_session.query(SystemAuditLog).all()
    assert len(logs) == 1
    assert logs[0].action_type == "INCIDENT_REPORT_CREATED"
    assert logs[0].entity_type == "incident_reports"
    assert logs[0].entity_id == report_id


def test_description_is_trimmed(client, sector):
    response = client.post(URL, json=body(sector, description="  Road blocked  "))
    assert response.status_code == 201
    assert response.json()["description"] == "Road blocked"


@pytest.mark.parametrize("field", ["sector_id", "event_date", "description"])
def test_missing_required_field_is_rejected(client, sector, db_session, field):
    data = body(sector)
    del data[field]
    assert client.post(URL, json=data).status_code == 422
    assert count_reports(db_session) == 0


@pytest.mark.parametrize("description", ["", "   ", "x" * 2001])
def test_blank_or_too_long_description_is_rejected(
    client, sector, db_session, description
):
    response = client.post(URL, json=body(sector, description=description))
    assert response.status_code == 422
    assert count_reports(db_session) == 0


@pytest.mark.parametrize("sector_id", [str(uuid4()), "Bwira"])
def test_unknown_or_malformed_sector_is_rejected(client, sector, db_session, sector_id):
    response = client.post(URL, json=body(sector, sector_id=sector_id))
    assert response.status_code == 422
    assert count_reports(db_session) == 0


def test_future_event_date_is_rejected(client, sector, db_session):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert client.post(URL, json=body(sector, event_date=future)).status_code == 422
    assert count_reports(db_session) == 0


def test_event_date_without_timezone_is_rejected(client, sector, db_session):
    response = client.post(URL, json=body(sector, event_date="2026-10-14T08:15:00"))
    assert response.status_code == 422
    assert count_reports(db_session) == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "SUBMITTED"},
        {"reported_by": str(uuid4())},
        {"reported_at": "2020-01-01T00:00:00+00:00"},
        {"report_id": str(uuid4())},
        {"latitude": -1.94},
    ],
)
def test_client_cannot_send_server_or_unknown_fields(client, sector, db_session, extra):
    assert client.post(URL, json=body(sector, **extra)).status_code == 422
    assert count_reports(db_session) == 0


def test_list_returns_newest_first_with_names(
    client, sector, db_session, make_incident, make_user
):
    reporter = make_user(full_name="Analyst One")
    older = make_incident(
        sector,
        reported_by_user=reporter,
        reported_at=datetime(2026, 10, 13, 14, 22, tzinfo=timezone.utc),
        description="Older report",
    )
    newer = make_incident(
        sector,
        reported_by_user=reporter,
        reported_at=datetime(2026, 10, 14, 10, 30, tzinfo=timezone.utc),
        description="Newer report",
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get(URL)

    assert response.status_code == 200
    data = response.json()
    assert [item["description"] for item in data] == ["Newer report", "Older report"]
    assert data[0]["district_name"] == "Ngororero"
    assert data[0]["reporter_name"] == "Analyst One"
    assert "status" not in data[0]


def test_list_is_empty_when_there_are_no_reports(client):
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == []


def test_list_paging_returns_the_requested_slice(client, sector):
    for n in range(3):
        client.post(URL, json=body(sector, description=f"Report {n}"))

    response = client.get(URL, params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_list_paging_limits_are_enforced(client, params):
    assert client.get(URL, params=params).status_code == 422


def test_get_one_returns_the_report(client, sector):
    report_id = client.post(URL, json=body(sector)).json()["report_id"]

    response = client.get(f"{URL}/{report_id}")

    assert response.status_code == 200
    assert response.json()["report_id"] == report_id
    assert response.json()["sector_name"] == "Bwira"


def test_get_one_unknown_id_returns_404(client):
    assert client.get(f"{URL}/{uuid4()}").status_code == 404


def test_get_one_malformed_id_returns_422(client):
    assert client.get(f"{URL}/not-a-uuid").status_code == 422
