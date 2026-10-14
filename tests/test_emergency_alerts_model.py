import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from models._enums import AlertChannel, AlertSeverity, AlertStatus
from models.emergency_alerts_model import EmergencyAlert
from models.risk_reviews_model import RiskReview


def test_new_alert_defaults_to_pending_review(
    db_session, make_alert, assert_recent_utc, make_inference, make_sector
):
    alert = make_alert(make_inference(make_sector()))
    db_session.add(alert)
    db_session.flush()

    assert alert.alert_status == AlertStatus.PENDING_REVIEW
    assert_recent_utc(alert.created_at)


def test_alert_fields_round_trip(db_session, make_alert, make_inference, make_sector):
    alert = make_alert(
        make_inference(make_sector()),
        alert_message="Evacuate the lower slope.",
        severity=AlertSeverity.CRITICAL,
        channel=AlertChannel.EMAIL,
        alert_status=AlertStatus.APPROVED,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(EmergencyAlert, alert.alert_id)
    assert loaded.alert_message == "Evacuate the lower slope."
    assert loaded.severity == AlertSeverity.CRITICAL
    assert loaded.channel == AlertChannel.EMAIL
    assert loaded.alert_status == AlertStatus.APPROVED


@pytest.mark.parametrize("column", ["alert_message", "severity", "channel"])
def test_required_columns_reject_null(
    db_session, column, make_alert, make_inference, make_sector
):
    db_session.add(make_alert(make_inference(make_sector()), **{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_requires_an_inference(db_session, make_sector):
    sector = make_sector()
    db_session.add(
        EmergencyAlert(
            sector=sector,
            alert_message="x",
            severity=AlertSeverity.HIGH,
            channel=AlertChannel.SMS,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_requires_a_sector(db_session, make_inference, make_sector, make_alert):
    inference = make_inference(make_sector())
    db_session.add(make_alert(inference, sector=None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_inference_must_exist(db_session, make_sector):
    sector = make_sector()
    db_session.add(sector)
    db_session.flush()
    db_session.add(
        EmergencyAlert(
            inference_id=uuid.uuid4(),
            sector_id=sector.sector_id,
            alert_message="x",
            severity=AlertSeverity.HIGH,
            channel=AlertChannel.SMS,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_links_both_ways_to_inference_and_sector(
    db_session, make_sector, make_inference, make_alert
):
    sector = make_sector()
    inference = make_inference(sector)
    alert = make_alert(inference)
    db_session.add(alert)
    db_session.flush()

    assert alert.inference is inference
    assert alert.sector is sector
    assert inference.emergency_alerts == [alert]
    assert sector.emergency_alerts == [alert]


def test_alert_lists_its_reviews(
    db_session, make_user, make_alert, make_review, make_inference, make_sector
):
    reviewer = make_user()
    alert = make_alert(make_inference(make_sector()))
    review = make_review(reviewer, alert=alert)
    db_session.add_all([reviewer, alert, review])
    db_session.flush()

    assert alert.risk_reviews == [review]
    assert review.alert is alert


def test_deleting_an_alert_deletes_its_reviews_but_not_the_inference(
    db_session, make_user, make_inference, make_alert, make_sector, make_review
):
    reviewer = make_user()
    inference = make_inference(make_sector())
    alert = make_alert(inference)
    db_session.add_all([reviewer, alert, make_review(reviewer, alert=alert)])
    db_session.commit()

    db_session.delete(alert)
    db_session.commit()

    assert db_session.query(EmergencyAlert).count() == 0
    assert db_session.query(RiskReview).count() == 0
    assert inference in db_session
