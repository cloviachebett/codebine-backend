"""Tests for the IncidentReport model."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import IncidentStatus
from models.incident_reports import IncidentReport


def test_new_report_defaults_to_submitted(
    db_session, make_incident, assert_recent_utc, make_sector
):
    report = make_incident(make_sector())
    db_session.add(report)
    db_session.flush()

    assert report.status is IncidentStatus.SUBMITTED
    assert report.reported_by is None
    assert_recent_utc(report.reported_at)


def test_report_persists_and_reloads(db_session, make_sector, make_incident):
    sector = make_sector()
    report = make_incident(
        sector,
        event_date=datetime(2026, 4, 2, tzinfo=timezone.utc),
        latitude=Decimal("-1.9441"),
        longitude=Decimal("30.0619"),
        description="Road cut off near the school.",
    )
    db_session.add(report)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(IncidentReport, report.report_id)
    assert loaded.sector_id == sector.sector_id
    # SQLite drops tzinfo on reload, so compare the wall-clock value.
    assert loaded.event_date.replace(tzinfo=None) == datetime(2026, 4, 2)
    assert loaded.latitude == Decimal("-1.944100")
    assert loaded.longitude == Decimal("30.061900")
    assert loaded.description == "Road cut off near the school."


def test_reporter_is_optional_so_anonymous_reports_work(
    db_session, make_incident, make_sector
):
    report = make_incident(make_sector(), reported_by_user=None)
    db_session.add(report)
    db_session.flush()
    assert report.reported_by_user is None


def test_reporter_link_works_both_ways(
    db_session, make_user, make_incident, make_sector
):
    user = make_user()
    report = make_incident(make_sector(), reported_by_user=user)
    db_session.add(report)
    db_session.flush()

    assert report.reported_by == user.user_id
    assert user.incident_reports == [report]


def test_reporter_must_exist(db_session, make_incident, make_sector):
    db_session.add(make_incident(make_sector(), reported_by=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_status_moves_through_the_review_workflow(
    db_session, make_incident, make_sector
):
    report = make_incident(make_sector())
    db_session.add(report)
    db_session.commit()

    for status in (
        IncidentStatus.UNDER_REVIEW,
        IncidentStatus.VERIFIED,
    ):
        report.status = status
        db_session.commit()
        db_session.expire_all()
        assert report.status is status


@pytest.mark.parametrize("status", list(IncidentStatus))
def test_every_status_can_be_stored(db_session, status, make_incident, make_sector):
    report = make_incident(make_sector(), status=status)
    db_session.add(report)
    db_session.commit()
    db_session.expire_all()
    assert report.status is status


def test_unknown_status_is_rejected(db_session, make_incident, make_sector):
    db_session.add(make_incident(make_sector(), status="CLOSED"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_sector_is_required(db_session, make_incident):
    db_session.add(make_incident(None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_must_exist(db_session):
    db_session.add(
        IncidentReport(
            sector_id=uuid.uuid4(),
            event_date=datetime(2026, 4, 2, tzinfo=timezone.utc),
            latitude=Decimal("-1.9441"),
            longitude=Decimal("30.0619"),
            description="x",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    "column", ["event_date", "latitude", "longitude", "description"]
)
def test_required_columns_reject_null(db_session, column, make_incident, make_sector):
    db_session.add(make_incident(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_report_links_back_to_its_sector(db_session, make_sector, make_incident):
    sector = make_sector()
    report = make_incident(sector)
    db_session.add(report)
    db_session.flush()

    assert report.sector is sector
    assert sector.incident_reports == [report]
