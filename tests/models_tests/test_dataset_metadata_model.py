"""Tests for the DatasetMetadata model."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import DatasetFactorType, ProcessingStatus
from models.dataset_metadata import DatasetMetadata


def test_new_dataset_defaults_to_pending(db_session, make_dataset):
    dataset = make_dataset()
    db_session.add(dataset)
    db_session.flush()

    assert dataset.processing_status is ProcessingStatus.PENDING
    assert dataset.last_processed_at is None
    assert dataset.rainfall_matrices == []


def test_dataset_persists_and_reloads(db_session, make_dataset):
    processed = datetime(2026, 4, 1, 6, 30, tzinfo=timezone.utc)
    dataset = make_dataset(
        dataset_name="NISR 2006 Sector Polygons",
        factor_type=DatasetFactorType.INVENTORY,
        source_name="NISR",
        file_path="datasets/nisr_2006_sectors.geojson",
        version="2006-r1",
        processing_status=ProcessingStatus.READY,
        last_processed_at=processed,
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(DatasetMetadata, dataset.dataset_id)
    assert loaded.dataset_name == "NISR 2006 Sector Polygons"
    assert loaded.factor_type is DatasetFactorType.INVENTORY
    assert loaded.source_name == "NISR"
    assert loaded.file_path == "datasets/nisr_2006_sectors.geojson"
    assert loaded.version == "2006-r1"
    assert loaded.processing_status is ProcessingStatus.READY
    # SQLite drops tzinfo on reload, so compare the wall-clock value.
    assert loaded.last_processed_at.replace(tzinfo=None) == datetime(2026, 4, 1, 6, 30)


@pytest.mark.parametrize(
    "column",
    ["dataset_name", "factor_type", "source_name", "file_path", "version"],
)
def test_required_columns_reject_null(db_session, column, make_dataset):
    db_session.add(make_dataset(**{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("factor_type", list(DatasetFactorType))
def test_every_factor_type_can_be_stored(db_session, factor_type, make_dataset):
    dataset = make_dataset(factor_type=factor_type)
    db_session.add(dataset)
    db_session.commit()
    db_session.expire_all()
    assert dataset.factor_type is factor_type


def test_unknown_factor_type_is_rejected(db_session, make_dataset):
    db_session.add(make_dataset(factor_type="WEATHER"))
    with pytest.raises(StatementError):
        db_session.flush()


@pytest.mark.parametrize("status", list(ProcessingStatus))
def test_every_processing_status_can_be_stored(db_session, status, make_dataset):
    dataset = make_dataset(processing_status=status)
    db_session.add(dataset)
    db_session.commit()
    db_session.expire_all()
    assert dataset.processing_status is status


def test_unknown_processing_status_is_rejected(db_session, make_dataset):
    db_session.add(make_dataset(processing_status="DONE"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_dataset_lists_the_rainfall_rows_it_supplied(
    db_session, make_dataset, make_rainfall, make_sector
):
    dataset = make_dataset()
    sector = make_sector()
    first = make_rainfall(
        sector,
        dataset=dataset,
        observation_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    second = make_rainfall(
        sector,
        dataset=dataset,
        observation_time=datetime(2026, 4, 2, tzinfo=timezone.utc),
    )
    db_session.add_all([dataset, first, second])
    db_session.flush()

    assert set(dataset.rainfall_matrices) == {first, second}
