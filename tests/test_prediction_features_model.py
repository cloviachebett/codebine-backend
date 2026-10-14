import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from models import PredictionFeature
from tests.factories import make_feature_snapshot, make_inference, make_sector
from tests.helpers import assert_recent_utc, count_rows


def test_snapshot_links_both_ways(session):
    inference = make_inference(make_sector())
    snapshot = make_feature_snapshot(inference)
    session.add(inference)
    session.flush()

    assert snapshot.inference_id == inference.inference_id
    assert inference.feature_snapshot is snapshot
    assert snapshot.inference is inference
    assert_recent_utc(snapshot.created_at)


def test_assigning_from_the_inference_side_also_links_both_ways(session):
    inference = make_inference(make_sector())
    snapshot = PredictionFeature(historical_features={"rain_7day": 10})
    inference.feature_snapshot = snapshot
    session.add(inference)
    session.flush()

    assert snapshot.inference is inference
    assert snapshot.inference_id == inference.inference_id


def test_historical_features_round_trip_as_json(session):
    features = {"rain_7day": 84.2, "history": [{"d": "2026-04-01", "mm": 12.5}]}
    inference = make_inference(make_sector())
    snapshot = make_feature_snapshot(inference, historical_features=features)
    session.add(inference)
    session.commit()
    session.expire_all()

    assert (
        session.get(PredictionFeature, snapshot.feature_snapshot_id).historical_features
        == features
    )


def test_historical_features_are_required(session):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference, historical_features=None)
    session.add(inference)
    with pytest.raises(IntegrityError):
        session.flush()


def test_an_inference_can_only_have_one_snapshot_row(session):
    inference = make_inference(make_sector())
    session.add(inference)
    session.flush()

    session.add_all(
        [
            PredictionFeature(
                inference_id=inference.inference_id, historical_features={"a": 1}
            ),
            PredictionFeature(
                inference_id=inference.inference_id, historical_features={"a": 2}
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_a_snapshot_is_replaced_by_clearing_the_old_one_first(session):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference, historical_features={"version": 1})
    session.add(inference)
    session.commit()

    inference.feature_snapshot = None
    session.flush()
    inference.feature_snapshot = PredictionFeature(historical_features={"version": 2})
    session.commit()

    assert count_rows(session, PredictionFeature) == 1
    assert inference.feature_snapshot.historical_features == {"version": 2}


def test_snapshot_requires_an_inference(session):
    session.add(PredictionFeature(historical_features={"a": 1}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_snapshot_inference_must_exist(session):
    session.add(
        PredictionFeature(inference_id=uuid.uuid4(), historical_features={"a": 1})
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_an_inference_deletes_its_snapshot(session):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference)
    session.add(inference)
    session.commit()

    session.delete(inference)
    session.commit()

    assert count_rows(session, PredictionFeature) == 0
