import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models import EmergencyAlert, RiskInference, RiskReview
from models._enums import RiskLevel
from tests.factories import (
    make_alert,
    make_inference,
    make_model_version,
    make_review,
    make_sector,
    make_user,
)
from tests.helpers import assert_recent_utc, count_rows


def test_new_inference_defaults(session):
    inference = make_inference(make_sector())
    session.add(inference)
    session.flush()

    assert_recent_utc(inference.prediction_time)
    assert inference.model_version_id is None
    assert inference.feature_snapshot is None
    assert inference.emergency_alerts == []
    assert inference.risk_reviews == []


def test_score_and_level_round_trip(session):
    inference = make_inference(
        make_sector(), risk_level=RiskLevel.EXTREME, risk_score=Decimal("0.93417")
    )
    session.add(inference)
    session.commit()
    session.expire_all()

    loaded = session.get(RiskInference, inference.inference_id)
    assert loaded.risk_level is RiskLevel.EXTREME
    assert loaded.risk_score == Decimal("0.93417")


@pytest.mark.parametrize("score", [Decimal("-0.00001"), Decimal("1.00001"), Decimal(5)])
def test_score_outside_zero_to_one_is_rejected(session, score):
    session.add(make_inference(make_sector(), risk_score=score))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("score", [Decimal(0), Decimal(1), Decimal("0.5")])
def test_score_at_the_boundaries_is_accepted(session, score):
    session.add(make_inference(make_sector(), risk_score=score))
    session.flush()


@pytest.mark.parametrize("level", list(RiskLevel))
def test_every_risk_level_can_be_stored(session, level):
    inference = make_inference(make_sector(), risk_level=level)
    session.add(inference)
    session.commit()
    session.expire_all()
    assert inference.risk_level is level


def test_unknown_risk_level_is_rejected(session):
    session.add(make_inference(make_sector(), risk_level="CRITICAL"))
    with pytest.raises(StatementError):
        session.flush()


@pytest.mark.parametrize("column", ["risk_level", "risk_score"])
def test_required_columns_reject_null(session, column):
    session.add(make_inference(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_sector_is_required(session):
    session.add(make_inference(None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_sector_must_exist(session):
    session.add(
        RiskInference(
            sector_id=uuid.uuid4(),
            risk_level=RiskLevel.LOW,
            risk_score=Decimal("0.1"),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_inference_links_to_sector_and_model_version(session):
    sector = make_sector()
    version = make_model_version()
    inference = make_inference(sector, model_version=version)
    session.add(inference)
    session.flush()

    assert inference.sector_id == sector.sector_id
    assert inference.model_version_id == version.model_version_id
    assert sector.risk_inferences == [inference]
    assert version.risk_inferences == [inference]


def test_deleting_an_inference_deletes_its_alerts_and_reviews(session):
    reviewer = make_user()
    inference = make_inference(make_sector())
    alert = make_alert(inference)
    session.add_all(
        [
            reviewer,
            inference,
            make_review(reviewer, inference=inference),
            make_review(reviewer, alert=alert),
        ]
    )
    session.commit()

    session.delete(inference)
    session.commit()

    assert count_rows(session, RiskInference) == 0
    assert count_rows(session, EmergencyAlert) == 0
    assert count_rows(session, RiskReview) == 0
