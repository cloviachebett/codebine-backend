import uuid

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import ReviewDecision
from models.risk_reviews_model import RiskReview


@pytest.fixture
def reviewer(db_session, make_user):
    user = make_user()
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def inference(db_session, make_inference, make_sector):
    inference = make_inference(make_sector())
    db_session.add(inference)
    db_session.flush()
    return inference


def test_review_of_an_inference(db_session, reviewer, inference, make_review):
    review = make_review(reviewer, inference=inference, comments="Matches field data.")
    db_session.add(review)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(RiskReview, review.review_id)
    assert loaded.inference_id == inference.inference_id
    assert loaded.alert_id is None
    assert loaded.reviewed_by == reviewer.user_id
    assert loaded.decision is ReviewDecision.APPROVED
    assert loaded.comments == "Matches field data."


def test_review_of_an_alert(db_session, reviewer, inference, make_alert, make_review):
    alert = make_alert(inference)
    review = make_review(reviewer, alert=alert, decision=ReviewDecision.DISMISSED)
    db_session.add_all([alert, review])
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(RiskReview, review.review_id)
    assert loaded.alert_id == alert.alert_id
    assert loaded.inference_id is None
    assert loaded.decision is ReviewDecision.DISMISSED


def test_review_cannot_target_both_an_inference_and_an_alert(
    db_session, reviewer, inference, make_alert, make_review
):
    alert = make_alert(inference)
    db_session.add_all([alert, make_review(reviewer, inference=inference, alert=alert)])
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_review_must_target_something(db_session, reviewer, make_review):
    db_session.add(make_review(reviewer))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_reviewer_is_required(db_session, inference, make_review):
    db_session.add(make_review(None, inference=inference))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_reviewer_must_exist(db_session, inference):
    db_session.add(
        RiskReview(
            inference_id=inference.inference_id,
            reviewed_by=uuid.uuid4(),
            decision=ReviewDecision.APPROVED,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_decision_is_required(db_session, reviewer, inference, make_review):
    db_session.add(make_review(reviewer, inference=inference, decision=None))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("decision", list(ReviewDecision))
def test_every_decision_can_be_stored(
    db_session, reviewer, inference, decision, make_review
):
    review = make_review(reviewer, inference=inference, decision=decision)
    db_session.add(review)
    db_session.commit()
    db_session.expire_all()
    assert review.decision is decision


def test_unknown_decision_is_rejected(db_session, reviewer, inference, make_review):
    db_session.add(make_review(reviewer, inference=inference, decision="MAYBE"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_comments_are_optional_and_timestamp_is_set(
    db_session, reviewer, inference, make_review, assert_recent_utc
):
    review = make_review(reviewer, inference=inference)
    db_session.add(review)
    db_session.flush()

    assert review.comments is None
    assert_recent_utc(review.reviewed_at)


def test_review_links_back_to_user_and_inference(
    db_session, reviewer, inference, make_review
):
    review = make_review(reviewer, inference=inference)
    db_session.add(review)
    db_session.flush()

    assert review.reviewed_by_user is reviewer
    assert review.inference is inference
    assert reviewer.risk_reviews == [review]
    assert inference.risk_reviews == [review]
