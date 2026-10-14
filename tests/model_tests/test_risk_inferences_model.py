import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import RiskLevel
from models.emergency_alerts import EmergencyAlert
from models.risk_inferences import RiskInference
from models.risk_reviews import RiskReview


def test_new_inference_defaults(
    db_session, make_inference, assert_recent_utc, make_sector
):
    inference = make_inference(make_sector())
    db_session.add(inference)
    db_session.flush()

    assert_recent_utc(inference.prediction_time)
    assert inference.model_version_id is None
    assert inference.feature_snapshot is None
    assert inference.emergency_alerts == []
    assert inference.risk_reviews == []


def test_score_and_level_round_trip(db_session, make_inference, make_sector):
    inference = make_inference(
        make_sector(), risk_level=RiskLevel.EXTREME, risk_score=Decimal("0.93417")
    )
    db_session.add(inference)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(RiskInference, inference.inference_id)
    assert loaded.risk_level is RiskLevel.EXTREME
    assert loaded.risk_score == Decimal("0.93417")


@pytest.mark.parametrize("score", [Decimal("-0.00001"), Decimal("1.00001"), Decimal(5)])
def test_score_outside_zero_to_one_is_rejected(
    db_session, score, make_inference, make_sector
):
    db_session.add(make_inference(make_sector(), risk_score=score))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("score", [Decimal(0), Decimal(1), Decimal("0.5")])
def test_score_at_the_boundaries_is_accepted(
    db_session, score, make_inference, make_sector
):
    db_session.add(make_inference(make_sector(), risk_score=score))
    db_session.flush()


@pytest.mark.parametrize("level", list(RiskLevel))
def test_every_risk_level_can_be_stored(db_session, level, make_inference, make_sector):
    inference = make_inference(make_sector(), risk_level=level)
    db_session.add(inference)
    db_session.commit()
    db_session.expire_all()
    assert inference.risk_level is level


def test_unknown_risk_level_is_rejected(db_session, make_inference, make_sector):
    db_session.add(make_inference(make_sector(), risk_level="CRITICAL"))
    with pytest.raises(StatementError):
        db_session.flush()


@pytest.mark.parametrize("column", ["risk_level", "risk_score"])
def test_required_columns_reject_null(db_session, column, make_inference, make_sector):
    db_session.add(make_inference(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_is_required(db_session, make_inference):
    db_session.add(make_inference(None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_must_exist(db_session):
    db_session.add(
        RiskInference(
            sector_id=uuid.uuid4(),
            risk_level=RiskLevel.LOW,
            risk_score=Decimal("0.1"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_inference_links_to_sector_and_model_version(
    db_session, make_sector, make_model_version, make_inference
):
    sector = make_sector()
    version = make_model_version()
    inference = make_inference(sector, model_version=version)
    db_session.add(inference)
    db_session.flush()

    assert inference.sector_id == sector.sector_id
    assert inference.model_version_id == version.model_version_id
    assert sector.risk_inferences == [inference]
    assert version.risk_inferences == [inference]


def test_deleting_an_inference_deletes_its_alerts_and_reviews(
    db_session, make_user, make_inference, make_alert, make_sector, make_review
):
    reviewer = make_user()
    inference = make_inference(make_sector())
    alert = make_alert(inference)
    db_session.add_all(
        [
            reviewer,
            inference,
            make_review(reviewer, inference=inference),
            make_review(reviewer, alert=alert),
        ]
    )
    db_session.commit()

    db_session.delete(inference)
    db_session.commit()

    assert db_session.query(RiskInference).count() == 0
    assert db_session.query(EmergencyAlert).count() == 0
    assert db_session.query(RiskReview).count() == 0
