import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models import IncidentReport
from models._enums import IncidentStatus
from tests.factories import make_incident, make_sector, make_user
from tests.helpers import assert_recent_utc


def test_new_report_defaults_to_submitted(session):
    report = make_incident(make_sector())
    session.add(report)
    session.flush()

    assert report.status is IncidentStatus.SUBMITTED
    assert report.reported_by is None
    assert report.latitude is None
    assert report.longitude is None
    assert_recent_utc(report.reported_at)


def test_report_persists_and_reloads(session):
    sector = make_sector()
    report = make_incident(
        sector,
        event_date=date(2026, 4, 2),
        latitude=Decimal("-1.9441"),
        longitude=Decimal("30.0619"),
        description="Road cut off near the school.",
    )
    session.add(report)
    session.commit()
    session.expire_all()

    loaded = session.get(IncidentReport, report.report_id)
    assert loaded.sector_id == sector.sector_id
    assert loaded.event_date == date(2026, 4, 2)
    assert loaded.latitude == Decimal("-1.944100")
    assert loaded.longitude == Decimal("30.061900")
    assert loaded.description == "Road cut off near the school."


def test_reporter_is_optional_so_anonymous_reports_work(session):
    report = make_incident(make_sector(), reported_by_user=None)
    session.add(report)
    session.flush()
    assert report.reported_by_user is None


def test_reporter_link_works_both_ways(session):
    user = make_user()
    report = make_incident(make_sector(), reported_by_user=user)
    session.add(report)
    session.flush()

    assert report.reported_by == user.user_id
    assert user.incident_reports == [report]


def test_reporter_must_exist(session):
    session.add(make_incident(make_sector(), reported_by=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        session.flush()


def test_status_moves_through_the_review_workflow(session):
    report = make_incident(make_sector())
    session.add(report)
    session.commit()

    for status in (
        IncidentStatus.UNDER_REVIEW,
        IncidentStatus.VERIFIED,
    ):
        report.status = status
        session.commit()
        session.expire_all()
        assert report.status is status


@pytest.mark.parametrize("status", list(IncidentStatus))
def test_every_status_can_be_stored(session, status):
    report = make_incident(make_sector(), status=status)
    session.add(report)
    session.commit()
    session.expire_all()
    assert report.status is status


def test_unknown_status_is_rejected(session):
    session.add(make_incident(make_sector(), status="CLOSED"))
    with pytest.raises(StatementError):
        session.flush()


def test_sector_is_required(session):
    session.add(make_incident(None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_sector_must_exist(session):
    session.add(
        IncidentReport(
            sector_id=uuid.uuid4(),
            event_date=date(2026, 4, 2),
            description="x",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("column", ["event_date", "description"])
def test_required_columns_reject_null(session, column):
    session.add(make_incident(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_report_links_back_to_its_sector(session):
    sector = make_sector()
    report = make_incident(sector)
    session.add(report)
    session.flush()

    assert report.sector is sector
    assert sector.incident_reports == [report]
