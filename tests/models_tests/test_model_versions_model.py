"""Tests for the ModelVersion model."""

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import ModelStatus
from models.model_versions import ModelVersion

METRICS = ["precision", "recall", "f1_score"]


def test_new_model_version_starts_in_training(db_session, make_model_version):
    version = make_model_version()
    db_session.add(version)
    db_session.flush()

    assert version.model_status is ModelStatus.TRAINING
    assert version.created_at is not None


@pytest.mark.parametrize(
    "column",
    ["model_name", "version_code", "model_type", "model_path"] + METRICS,
)
def test_required_columns_reject_null(db_session, column, make_model_version):
    db_session.add(make_model_version(**{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_model_name_and_version_code_must_be_unique_together(
    db_session, make_model_version
):
    db_session.add(make_model_version(model_name="rf", version_code="v1"))
    db_session.flush()
    db_session.add(make_model_version(model_name="rf", version_code="v1"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_version_code_is_allowed_for_different_models(
    db_session, make_model_version
):
    db_session.add_all(
        [
            make_model_version(model_name="rf", version_code="v1"),
            make_model_version(model_name="xgb", version_code="v1"),
        ]
    )
    db_session.flush()


def test_same_model_can_have_several_versions(db_session, make_model_version):
    db_session.add_all(
        [
            make_model_version(model_name="rf", version_code="v1"),
            make_model_version(model_name="rf", version_code="v2"),
        ]
    )
    db_session.flush()


@pytest.mark.parametrize("column", METRICS)
def test_each_metric_round_trips_as_json(db_session, column, make_model_version):
    value = {
        "overall": 0.91,
        "per_class": {"LOW": 0.95, "HIGH": 0.84},
        "folds": [0.9, 0.92, 0.91],
    }
    version = make_model_version(**{column: value})
    db_session.add(version)
    db_session.commit()
    db_session.expire_all()

    assert getattr(db_session.get(ModelVersion, version.model_version_id), column) == (
        value
    )


@pytest.mark.parametrize("status", list(ModelStatus))
def test_every_status_can_be_stored(db_session, status, make_model_version):
    version = make_model_version(model_status=status)
    db_session.add(version)
    db_session.commit()
    db_session.expire_all()
    assert version.model_status is status


def test_unknown_status_is_rejected(db_session, make_model_version):
    db_session.add(make_model_version(model_status="LIVE"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_version_lists_its_inferences(
    db_session, make_model_version, make_inference, make_sector
):
    version = make_model_version()
    inference = make_inference(make_sector(), model_version=version)
    db_session.add_all([version, inference])
    db_session.flush()

    assert version.risk_inferences == [inference]
    assert inference.model_version_id == version.model_version_id


def test_a_version_with_inferences_cannot_be_deleted(
    db_session, make_model_version, make_inference, make_sector
):
    """model_version_id is required on an inference, so the database must
    refuse to remove a model version that predictions still point to."""
    version = make_model_version()
    inference = make_inference(make_sector(), model_version=version)
    db_session.add_all([version, inference])
    db_session.commit()

    db_session.delete(version)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_a_version_without_inferences_can_be_deleted(db_session, make_model_version):
    version = make_model_version()
    db_session.add(version)
    db_session.commit()

    db_session.delete(version)
    db_session.commit()
    assert db_session.query(ModelVersion).count() == 0
