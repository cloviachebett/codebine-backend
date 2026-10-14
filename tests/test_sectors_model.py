import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError

from models import (
    EmergencyAlert,
    IncidentReport,
    LandslideInventory,
    PredictionFeature,
    RainfallMatrix,
    RiskInference,
    RiskReview,
    Sector,
    User,
)
from models._enums import GeologyClass
from tests.factories import (
    make_alert,
    make_feature_snapshot,
    make_incident,
    make_inference,
    make_landslide,
    make_rainfall,
    make_review,
    make_sector,
    make_user,
)
from tests.helpers import assert_recent_utc, count_rows


def test_sector_persists_and_reloads(session):
    sector = make_sector(
        province_name="Western",
        mean_slope_deg=Decimal("31.25"),
        geology_class=GeologyClass.SCHIST,
        soil_features={"texture": "sandy loam", "layers": [10, 20]},
    )
    session.add(sector)
    session.commit()
    session.expire_all()

    loaded = session.get(Sector, sector.sector_id)
    assert loaded is not None
    assert loaded.province_name == "Western"
    assert loaded.mean_slope_deg == Decimal("31.25")
    assert loaded.geology_class is GeologyClass.SCHIST
    assert loaded.soil_features == {"texture": "sandy loam", "layers": [10, 20]}


def test_sector_generates_uuid_and_utc_timestamp(session):
    sector = make_sector()
    session.add(sector)
    session.flush()

    assert isinstance(sector.sector_id, uuid.UUID)
    assert_recent_utc(sector.created_at)


@pytest.mark.parametrize(
    "column",
    [
        "province_name",
        "district_name",
        "sector_name",
        "boundary_ref",
        "mean_slope_deg",
        "geology_class",
        "soil_features",
        "land_cover_class",
    ],
)
def test_required_columns_reject_null(session, column):
    session.add(make_sector(**{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_district_and_sector_name_must_be_unique_together(session):
    session.add(make_sector(district_name="Rutsiro", sector_name="Boneza"))
    session.flush()
    session.add(make_sector(district_name="Rutsiro", sector_name="Boneza"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_same_sector_name_allowed_in_different_districts(session):
    session.add_all(
        [
            make_sector(district_name="Rutsiro", sector_name="Central"),
            make_sector(district_name="Nyabihu", sector_name="Central"),
        ]
    )
    session.flush()
    assert count_rows(session, Sector) == 2


def test_negative_slope_is_rejected(session):
    session.add(make_sector(mean_slope_deg=Decimal("-0.01")))
    with pytest.raises(IntegrityError):
        session.flush()


def test_zero_slope_is_allowed(session):
    session.add(make_sector(mean_slope_deg=Decimal(0)))
    session.flush()
    assert count_rows(session, Sector) == 1


@pytest.mark.parametrize("geology", list(GeologyClass))
def test_every_geology_class_can_be_stored(session, geology):
    sector = make_sector(geology_class=geology)
    session.add(sector)
    session.commit()
    session.expire_all()
    assert session.get(Sector, sector.sector_id).geology_class is geology


def test_unknown_geology_class_is_rejected_by_the_orm(session):
    session.add(make_sector(geology_class="MARBLE"))
    with pytest.raises(StatementError):
        session.flush()


def test_unknown_geology_class_is_rejected_by_the_database(session):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO sectors (sector_id, province_name, district_name, "
                "sector_name, boundary_ref, mean_slope_deg, geology_class, "
                "soil_features, land_cover_class, created_at) VALUES "
                "(:id, 'W', 'D', 'S', 'b', 10, 'MARBLE', '{}', 'Crop', "
                "'2026-01-01 00:00:00')"
            ),
            {"id": uuid.uuid4().hex},
        )


def test_sector_relationships_are_two_way(session):
    sector = make_sector()
    rainfall = make_rainfall(sector)
    landslide = make_landslide(sector)
    session.add(sector)
    session.flush()

    assert sector.rainfall_matrices == [rainfall]
    assert sector.landslide_inventory == [landslide]
    assert rainfall.sector is sector
    assert landslide.sector is sector


def test_deleting_a_sector_removes_everything_it_owns(session):
    sector = make_sector()
    reviewer = make_user()
    inference = make_inference(sector)
    make_feature_snapshot(inference)
    alert = make_alert(inference)
    session.add_all(
        [
            sector,
            reviewer,
            make_rainfall(sector),
            make_landslide(sector),
            make_incident(sector, reported_by_user=reviewer),
            make_review(reviewer, inference=inference),
            make_review(reviewer, alert=alert),
        ]
    )
    session.commit()

    session.delete(sector)
    session.commit()

    for model in (
        Sector,
        RainfallMatrix,
        LandslideInventory,
        RiskInference,
        PredictionFeature,
        EmergencyAlert,
        RiskReview,
        IncidentReport,
    ):
        assert count_rows(session, model) == 0, model.__name__
    assert count_rows(session, User) == 1
