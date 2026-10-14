import uuid

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models import RiskReview
from models._enums import ReviewDecision
from tests.factories import (
    make_alert,
    make_inference,
    make_review,
    make_sector,
    make_user,
)
from tests.helpers import assert_recent_utc


@pytest.fixture
def reviewer(session):
    user = make_user()
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def inference(session):
    inference = make_inference(make_sector())
    session.add(inference)
    session.flush()
    return inference


def test_review_of_an_inference(session, reviewer, inference):
    review = make_review(reviewer, inference=inference, comments="Matches field data.")
    session.add(review)
    session.commit()
    session.expire_all()

    loaded = session.get(RiskReview, review.review_id)
    assert loaded.inference_id == inference.inference_id
    assert loaded.alert_id is None
    assert loaded.reviewed_by == reviewer.user_id
    assert loaded.decision is ReviewDecision.APPROVED
    assert loaded.comments == "Matches field data."


def test_review_of_an_alert(session, reviewer, inference):
    alert = make_alert(inference)
    review = make_review(reviewer, alert=alert, decision=ReviewDecision.DISMISSED)
    session.add_all([alert, review])
    session.commit()
    session.expire_all()

    loaded = session.get(RiskReview, review.review_id)
    assert loaded.alert_id == alert.alert_id
    assert loaded.inference_id is None
    assert loaded.decision is ReviewDecision.DISMISSED


def test_review_cannot_target_both_an_inference_and_an_alert(
    session, reviewer, inference
):
    alert = make_alert(inference)
    session.add_all([alert, make_review(reviewer, inference=inference, alert=alert)])
    with pytest.raises(IntegrityError):
        session.flush()


def test_review_must_target_something(session, reviewer):
    session.add(make_review(reviewer))
    with pytest.raises(IntegrityError):
        session.flush()


def test_reviewer_is_required(session, inference):
    session.add(make_review(None, inference=inference))
    with pytest.raises(IntegrityError):
        session.flush()


def test_reviewer_must_exist(session, inference):
    session.add(
        RiskReview(
            inference_id=inference.inference_id,
            reviewed_by=uuid.uuid4(),
            decision=ReviewDecision.APPROVED,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_decision_is_required(session, reviewer, inference):
    session.add(make_review(reviewer, inference=inference, decision=None))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("decision", list(ReviewDecision))
def test_every_decision_can_be_stored(session, reviewer, inference, decision):
    review = make_review(reviewer, inference=inference, decision=decision)
    session.add(review)
    session.commit()
    session.expire_all()
    assert review.decision is decision


def test_unknown_decision_is_rejected(session, reviewer, inference):
    session.add(make_review(reviewer, inference=inference, decision="MAYBE"))
    with pytest.raises(StatementError):
        session.flush()


def test_comments_are_optional_and_timestamp_is_set(session, reviewer, inference):
    review = make_review(reviewer, inference=inference)
    session.add(review)
    session.flush()

    assert review.comments is None
    assert_recent_utc(review.reviewed_at)


def test_review_links_back_to_user_and_inference(session, reviewer, inference):
    review = make_review(reviewer, inference=inference)
    session.add(review)
    session.flush()

    assert review.reviewed_by_user is reviewer
    assert review.inference is inference
    assert reviewer.risk_reviews == [review]
    assert inference.risk_reviews == [review]
