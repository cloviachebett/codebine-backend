import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models import ModelVersion
from models._enums import ModelStatus
from tests.factories import make_inference, make_model_version, make_sector


def test_new_model_version_starts_in_training(session):
    version = make_model_version()
    session.add(version)
    session.flush()

    assert version.model_status is ModelStatus.TRAINING
    assert version.evaluation_metrics is None
    assert version.created_at is not None


@pytest.mark.parametrize(
    "column", ["model_name", "version_code", "model_type", "model_path"]
)
def test_required_columns_reject_null(session, column):
    session.add(make_model_version(**{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_model_name_and_version_code_must_be_unique_together(session):
    session.add(make_model_version(model_name="rf", version_code="v1"))
    session.flush()
    session.add(make_model_version(model_name="rf", version_code="v1"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_same_version_code_is_allowed_for_different_models(session):
    session.add_all(
        [
            make_model_version(model_name="rf", version_code="v1"),
            make_model_version(model_name="xgb", version_code="v1"),
        ]
    )
    session.flush()


def test_same_model_can_have_several_versions(session):
    session.add_all(
        [
            make_model_version(model_name="rf", version_code="v1"),
            make_model_version(model_name="rf", version_code="v2"),
        ]
    )
    session.flush()


def test_evaluation_metrics_round_trip_as_json(session):
    metrics = {
        "auc": 0.91,
        "recall": 0.84,
        "confusion": [[120, 8], [11, 61]],
        "notes": {"split": "2015-2022 train / 2023 test"},
    }
    version = make_model_version(evaluation_metrics=metrics)
    session.add(version)
    session.commit()
    session.expire_all()

    assert session.get(ModelVersion, version.model_version_id).evaluation_metrics == (
        metrics
    )


@pytest.mark.parametrize("status", list(ModelStatus))
def test_every_status_can_be_stored(session, status):
    version = make_model_version(model_status=status)
    session.add(version)
    session.commit()
    session.expire_all()
    assert version.model_status is status


def test_unknown_status_is_rejected(session):
    session.add(make_model_version(model_status="LIVE"))
    with pytest.raises(StatementError):
        session.flush()


def test_version_lists_its_inferences(session):
    version = make_model_version()
    inference = make_inference(make_sector(), model_version=version)
    session.add_all([version, inference])
    session.flush()

    assert version.risk_inferences == [inference]
    assert inference.model_version_id == version.model_version_id


def test_deleting_a_version_keeps_its_inferences_unlinked(session):
    version = make_model_version()
    inference = make_inference(make_sector(), model_version=version)
    session.add_all([version, inference])
    session.commit()

    session.delete(version)
    session.commit()
    session.refresh(inference)

    assert inference.model_version_id is None
