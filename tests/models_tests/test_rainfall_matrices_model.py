"""Tests for the RainfallMatrix model."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from models.rainfall_matrices import RainfallMatrix

WINDOWS = [
    "rain_1day_mm",
    "rain_3day_mm",
    "rain_7day_mm",
    "rain_10day_mm",
    "rain_30day_mm",
]


def _at(day: int) -> datetime:
    return datetime(2026, 4, day, tzinfo=timezone.utc)


def test_unset_accumulations_default_to_zero(db_session, make_rainfall, make_sector):
    rainfall = make_rainfall(make_sector())
    db_session.add(rainfall)
    db_session.commit()
    db_session.expire_all()

    for column in WINDOWS:
        assert getattr(rainfall, column) == Decimal(0)


def test_accumulations_round_trip_with_two_decimals(
    db_session, make_rainfall, make_sector
):
    rainfall = make_rainfall(
        make_sector(),
        rain_1day_mm=Decimal("12.34"),
        rain_3day_mm=Decimal("30.5"),
        rain_7day_mm=Decimal("84.25"),
        rain_10day_mm=Decimal("120.00"),
        rain_30day_mm=Decimal("999.99"),
    )
    db_session.add(rainfall)
    db_session.commit()
    db_session.expire_all()

    assert rainfall.rain_1day_mm == Decimal("12.34")
    assert rainfall.rain_3day_mm == Decimal("30.50")
    assert rainfall.rain_30day_mm == Decimal("999.99")


def test_observation_time_round_trips(db_session, make_rainfall, make_sector):
    rainfall = make_rainfall(make_sector(), observation_time=_at(5))
    db_session.add(rainfall)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(RainfallMatrix, rainfall.rainfall_id)
    # SQLite drops tzinfo on reload, so compare the wall-clock value.
    assert loaded.observation_time.replace(tzinfo=None) == datetime(2026, 4, 5)


def test_one_row_per_sector_and_observation_time(
    db_session, make_sector, make_rainfall
):
    sector = make_sector()
    db_session.add_all([sector, make_rainfall(sector, observation_time=_at(1))])
    db_session.flush()
    db_session.add(make_rainfall(sector, observation_time=_at(1)))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_time_is_allowed_for_different_sectors(
    db_session, make_sector, make_rainfall
):
    first, second = make_sector(), make_sector()
    db_session.add_all([make_rainfall(first), make_rainfall(second)])
    db_session.flush()
    assert first.rainfall_matrices[0].observation_time == _at(1)
    assert second.rainfall_matrices[0].observation_time == _at(1)


def test_different_times_are_allowed_for_one_sector(
    db_session, make_sector, make_rainfall
):
    sector = make_sector()
    db_session.add_all(
        [
            make_rainfall(sector, observation_time=_at(1)),
            make_rainfall(sector, observation_time=_at(2)),
        ]
    )
    db_session.flush()
    assert len(sector.rainfall_matrices) == 2


@pytest.mark.parametrize("column", WINDOWS)
def test_negative_rainfall_is_rejected_in_every_window(
    db_session, column, make_rainfall, make_sector
):
    db_session.add(make_rainfall(make_sector(), **{column: Decimal("-0.01")}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_is_required(db_session, make_rainfall):
    db_session.add(make_rainfall(None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_must_exist(db_session):
    db_session.add(RainfallMatrix(sector_id=uuid.uuid4(), observation_time=_at(1)))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_observation_time_is_required(db_session, make_rainfall, make_sector):
    db_session.add(make_rainfall(make_sector(), observation_time=None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dataset_is_optional(db_session, make_rainfall, make_sector):
    rainfall = make_rainfall(make_sector())
    db_session.add(rainfall)
    db_session.flush()
    assert rainfall.dataset_id is None
    assert rainfall.dataset is None


def test_rainfall_links_to_its_source_dataset(
    db_session, make_rainfall, make_sector, make_dataset
):
    dataset = make_dataset()
    rainfall = make_rainfall(make_sector(), dataset=dataset)
    db_session.add(rainfall)
    db_session.flush()

    assert rainfall.dataset_id == dataset.dataset_id
    assert dataset.rainfall_matrices == [rainfall]


def test_dataset_must_exist(db_session, make_rainfall, make_sector):
    db_session.add(make_rainfall(make_sector(), dataset_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        db_session.flush()
