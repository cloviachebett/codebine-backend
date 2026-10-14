import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from models.rainfall_matrices_model import RainfallMatrix

WINDOWS = ["rain_1day", "rain_3day", "rain_7day", "rain_10day", "rain_30day"]


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
        rain_1day=Decimal("12.34"),
        rain_3day=Decimal("30.5"),
        rain_7day=Decimal("84.25"),
        rain_10day=Decimal("120.00"),
        rain_30day=Decimal("999.99"),
    )
    db_session.add(rainfall)
    db_session.commit()
    db_session.expire_all()

    assert rainfall.rain_1day == Decimal("12.34")
    assert rainfall.rain_3day == Decimal("30.50")
    assert rainfall.rain_30day == Decimal("999.99")


def test_one_row_per_sector_and_date(db_session, make_sector, make_rainfall):
    sector = make_sector()
    db_session.add_all(
        [sector, make_rainfall(sector, observation_date=date(2026, 4, 1))]
    )
    db_session.flush()
    db_session.add(make_rainfall(sector, observation_date=date(2026, 4, 1)))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_date_is_allowed_for_different_sectors(
    db_session, make_sector, make_rainfall
):
    first, second = make_sector(), make_sector()
    db_session.add_all([make_rainfall(first), make_rainfall(second)])
    db_session.flush()
    assert first.rainfall_matrices[0].observation_date == date(2026, 4, 1)
    assert second.rainfall_matrices[0].observation_date == date(2026, 4, 1)


def test_different_dates_are_allowed_for_one_sector(
    db_session, make_sector, make_rainfall
):
    sector = make_sector()
    db_session.add_all(
        [
            make_rainfall(sector, observation_date=date(2026, 4, 1)),
            make_rainfall(sector, observation_date=date(2026, 4, 2)),
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
    db_session.add(
        RainfallMatrix(sector_id=uuid.uuid4(), observation_date=date(2026, 4, 1))
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_observation_date_is_required(db_session, make_rainfall, make_sector):
    db_session.add(make_rainfall(make_sector(), observation_date=None))
    with pytest.raises(IntegrityError):
        db_session.flush()
