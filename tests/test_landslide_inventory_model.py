import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from models import LandslideInventory
from models._enums import LandslideSeverity
from tests.factories import make_landslide, make_sector


def test_landslide_persists_and_reloads(session):
    sector = make_sector()
    landslide = make_landslide(
        sector,
        event_date=date(2023, 5, 3),
        severity=LandslideSeverity.HIGH,
        source_name="RNRA inventory",
        source_reference="RNRA-2023-114",
        description="Debris flow above the tea factory.",
    )
    session.add(landslide)
    session.commit()
    session.expire_all()

    loaded = session.get(LandslideInventory, landslide.landslide_id)
    assert loaded.sector_id == sector.sector_id
    assert loaded.event_date == date(2023, 5, 3)
    assert loaded.severity is LandslideSeverity.HIGH
    assert loaded.source_reference == "RNRA-2023-114"
    assert loaded.description == "Debris flow above the tea factory."


def test_optional_fields_default_to_null(session):
    landslide = make_landslide(make_sector())
    session.add(landslide)
    session.commit()
    session.expire_all()

    assert landslide.severity is None
    assert landslide.latitude is None
    assert landslide.longitude is None
    assert landslide.source_reference is None
    assert landslide.description is None


def test_coordinates_round_trip_with_six_decimals(session):
    landslide = make_landslide(
        make_sector(), latitude=Decimal("-1.947500"), longitude=Decimal("29.874321")
    )
    session.add(landslide)
    session.commit()
    session.expire_all()

    assert landslide.latitude == Decimal("-1.947500")
    assert landslide.longitude == Decimal("29.874321")


@pytest.mark.parametrize("severity", list(LandslideSeverity))
def test_every_severity_can_be_stored(session, severity):
    landslide = make_landslide(make_sector(), severity=severity)
    session.add(landslide)
    session.commit()
    session.expire_all()
    assert landslide.severity is severity


def test_unknown_severity_is_rejected(session):
    session.add(make_landslide(make_sector(), severity="CATASTROPHIC"))
    with pytest.raises(StatementError):
        session.flush()


def test_sector_is_required(session):
    session.add(make_landslide(None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_sector_must_exist(session):
    session.add(
        LandslideInventory(
            sector_id=uuid.uuid4(),
            event_date=date(2023, 5, 3),
            source_name="RNRA inventory",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("column", ["event_date", "source_name"])
def test_required_columns_reject_null(session, column):
    session.add(make_landslide(make_sector(), **{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()
