import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import LandslideSeverity
from models.landslide_inventory import LandslideInventory


def test_landslide_persists_and_reloads(db_session, make_sector, make_landslide):
    sector = make_sector()
    landslide = make_landslide(
        sector,
        event_date=date(2023, 5, 3),
        severity=LandslideSeverity.HIGH,
        source_name="RNRA inventory",
        source_reference="RNRA-2023-114",
        description="Debris flow above the tea factory.",
    )
    db_session.add(landslide)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(LandslideInventory, landslide.landslide_id)
    assert loaded.sector_id == sector.sector_id
    assert loaded.event_date == date(2023, 5, 3)
    assert loaded.severity is LandslideSeverity.HIGH
    assert loaded.source_reference == "RNRA-2023-114"
    assert loaded.description == "Debris flow above the tea factory."


def test_optional_fields_default_to_null(db_session, make_landslide, make_sector):
    landslide = make_landslide(make_sector())
    db_session.add(landslide)
    db_session.commit()
    db_session.expire_all()

    assert landslide.severity is None
    assert landslide.latitude is None
    assert landslide.longitude is None
    assert landslide.source_reference is None
    assert landslide.description is None


def test_coordinates_round_trip_with_six_decimals(
    db_session, make_landslide, make_sector
):
    landslide = make_landslide(
        make_sector(), latitude=Decimal("-1.947500"), longitude=Decimal("29.874321")
    )
    db_session.add(landslide)
    db_session.commit()
    db_session.expire_all()

    assert landslide.latitude == Decimal("-1.947500")
    assert landslide.longitude == Decimal("29.874321")


@pytest.mark.parametrize("severity", list(LandslideSeverity))
def test_every_severity_can_be_stored(
    db_session, severity, make_landslide, make_sector
):
    landslide = make_landslide(make_sector(), severity=severity)
    db_session.add(landslide)
    db_session.commit()
    db_session.expire_all()
    assert landslide.severity is severity


def test_unknown_severity_is_rejected(db_session, make_landslide, make_sector):
    db_session.add(make_landslide(make_sector(), severity="CATASTROPHIC"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_sector_is_required(db_session, make_landslide):
    db_session.add(make_landslide(None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sector_must_exist(db_session):
    db_session.add(
        LandslideInventory(
            sector_id=uuid.uuid4(),
            event_date=date(2023, 5, 3),
            source_name="RNRA inventory",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("column", ["event_date", "source_name"])
def test_required_columns_reject_null(db_session, column, make_landslide, make_sector):
    db_session.add(make_landslide(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()
