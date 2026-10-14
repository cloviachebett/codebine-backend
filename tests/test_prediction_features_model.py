import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from models.prediction_features_model import PredictionFeature


def test_snapshot_links_both_ways(
    db_session, make_inference, make_feature_snapshot, assert_recent_utc, make_sector
):
    inference = make_inference(make_sector())
    snapshot = make_feature_snapshot(inference)
    db_session.add(inference)
    db_session.flush()

    assert snapshot.inference_id == inference.inference_id
    assert inference.feature_snapshot is snapshot
    assert snapshot.inference is inference
    assert_recent_utc(snapshot.created_at)


def test_assigning_from_the_inference_side_also_links_both_ways(
    db_session, make_inference, make_sector
):
    inference = make_inference(make_sector())
    snapshot = PredictionFeature(historical_features={"rain_7day": 10})
    inference.feature_snapshot = snapshot
    db_session.add(inference)
    db_session.flush()

    assert snapshot.inference is inference
    assert snapshot.inference_id == inference.inference_id


def test_historical_features_round_trip_as_json(
    db_session, make_inference, make_feature_snapshot, make_sector
):
    features = {"rain_7day": 84.2, "history": [{"d": "2026-04-01", "mm": 12.5}]}
    inference = make_inference(make_sector())
    snapshot = make_feature_snapshot(inference, historical_features=features)
    db_session.add(inference)
    db_session.commit()
    db_session.expire_all()

    assert (
        db_session.get(
            PredictionFeature, snapshot.feature_snapshot_id
        ).historical_features
        == features
    )


def test_historical_features_are_required(
    db_session, make_inference, make_feature_snapshot, make_sector
):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference, historical_features=None)
    db_session.add(inference)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_an_inference_can_only_have_one_snapshot_row(
    db_session, make_inference, make_sector
):
    inference = make_inference(make_sector())
    db_session.add(inference)
    db_session.flush()

    db_session.add_all(
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
        db_session.flush()


def test_a_snapshot_is_replaced_by_clearing_the_old_one_first(
    db_session, make_inference, make_feature_snapshot, make_sector
):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference, historical_features={"version": 1})
    db_session.add(inference)
    db_session.commit()

    inference.feature_snapshot = None
    db_session.flush()
    inference.feature_snapshot = PredictionFeature(historical_features={"version": 2})
    db_session.commit()

    assert db_session.query(PredictionFeature).count() == 1
    assert inference.feature_snapshot.historical_features == {"version": 2}


def test_snapshot_requires_an_inference(db_session):
    db_session.add(PredictionFeature(historical_features={"a": 1}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_snapshot_inference_must_exist(db_session):
    db_session.add(
        PredictionFeature(inference_id=uuid.uuid4(), historical_features={"a": 1})
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_an_inference_deletes_its_snapshot(
    db_session, make_inference, make_feature_snapshot, make_sector
):
    inference = make_inference(make_sector())
    make_feature_snapshot(inference)
    db_session.add(inference)
    db_session.commit()

    db_session.delete(inference)
    db_session.commit()

    assert db_session.query(PredictionFeature).count() == 0
