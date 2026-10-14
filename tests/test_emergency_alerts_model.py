import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from models import EmergencyAlert, RiskReview
from models._enums import AlertChannel, AlertSeverity, AlertStatus
from tests.factories import (
    make_alert,
    make_inference,
    make_review,
    make_sector,
    make_user,
)
from tests.helpers import assert_recent_utc, count_rows


def test_new_alert_defaults_to_pending_review(session):
    alert = make_alert(make_inference(make_sector()))
    session.add(alert)
    session.flush()

    assert alert.alert_status == AlertStatus.PENDING_REVIEW
    assert_recent_utc(alert.created_at)


def test_alert_fields_round_trip(session):
    alert = make_alert(
        make_inference(make_sector()),
        alert_message="Evacuate the lower slope.",
        severity=AlertSeverity.CRITICAL,
        channel=AlertChannel.EMAIL,
        alert_status=AlertStatus.APPROVED,
    )
    session.add(alert)
    session.commit()
    session.expire_all()

    loaded = session.get(EmergencyAlert, alert.alert_id)
    assert loaded.alert_message == "Evacuate the lower slope."
    assert loaded.severity == AlertSeverity.CRITICAL
    assert loaded.channel == AlertChannel.EMAIL
    assert loaded.alert_status == AlertStatus.APPROVED


@pytest.mark.parametrize("column", ["alert_message", "severity", "channel"])
def test_required_columns_reject_null(session, column):
    session.add(make_alert(make_inference(make_sector()), **{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_alert_requires_an_inference(session):
    sector = make_sector()
    session.add(
        EmergencyAlert(
            sector=sector,
            alert_message="x",
            severity=AlertSeverity.HIGH,
            channel=AlertChannel.SMS,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_alert_requires_a_sector(session):
    inference = make_inference(make_sector())
    session.add(make_alert(inference, sector=None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_alert_inference_must_exist(session):
    sector = make_sector()
    session.add(sector)
    session.flush()
    session.add(
        EmergencyAlert(
            inference_id=uuid.uuid4(),
            sector_id=sector.sector_id,
            alert_message="x",
            severity=AlertSeverity.HIGH,
            channel=AlertChannel.SMS,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_alert_links_both_ways_to_inference_and_sector(session):
    sector = make_sector()
    inference = make_inference(sector)
    alert = make_alert(inference)
    session.add(alert)
    session.flush()

    assert alert.inference is inference
    assert alert.sector is sector
    assert inference.emergency_alerts == [alert]
    assert sector.emergency_alerts == [alert]


def test_alert_lists_its_reviews(session):
    reviewer = make_user()
    alert = make_alert(make_inference(make_sector()))
    review = make_review(reviewer, alert=alert)
    session.add_all([reviewer, alert, review])
    session.flush()

    assert alert.risk_reviews == [review]
    assert review.alert is alert


def test_deleting_an_alert_deletes_its_reviews_but_not_the_inference(session):
    reviewer = make_user()
    inference = make_inference(make_sector())
    alert = make_alert(inference)
    session.add_all([reviewer, alert, make_review(reviewer, alert=alert)])
    session.commit()

    session.delete(alert)
    session.commit()

    assert count_rows(session, EmergencyAlert) == 0
    assert count_rows(session, RiskReview) == 0
    assert inference in session
