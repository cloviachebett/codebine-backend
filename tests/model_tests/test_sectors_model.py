import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import GeologyClass
from models.emergency_alerts import EmergencyAlert
from models.incident_reports import IncidentReport
from models.landslide_inventory import LandslideInventory
from models.prediction_features import PredictionFeature
from models.rainfall_matrices import RainfallMatrix
from models.risk_inferences import RiskInference
from models.risk_reviews import RiskReview
from models.sectors import Sector
from models.users import User


def test_sector_persists_and_reloads(db_session, make_sector):
    sector = make_sector(
        province_name="Western",
        mean_slope_deg=Decimal("31.25"),
        geology_class=GeologyClass.SCHIST,
        soil_features={
            "texture": "sandy loam",
            "layers": [10, 20],
        },  # Fixed missing arrays
    )
    db_session.add(sector)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(Sector, sector.sector_id)
    assert loaded is not None
    assert loaded.province_name == "Western"
    assert loaded.mean_slope_deg == Decimal("31.25")
    assert loaded.geology_class is GeologyClass.SCHIST
    assert loaded.soil_features == {
        "texture": "sandy loam",
        "layers": [10, 20],
    }


def test_sector_generates_uuid_and_utc_timestamp(
    db_session, make_sector, assert_recent_utc
):
    sector = make_sector()
    db_session.add(sector)
    db_session.flush()

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
def test_required_columns_reject_null(db_session, column, make_sector):
    db_session.add(make_sector(**{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_district_and_sector_name_must_be_unique_together(db_session, make_sector):
    db_session.add(make_sector(district_name="Rutsiro", sector_name="Boneza"))
    db_session.flush()
    db_session.add(make_sector(district_name="Rutsiro", sector_name="Boneza"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_sector_name_allowed_in_different_districts(db_session, make_sector):
    db_session.add_all(
        [
            make_sector(district_name="Rutsiro", sector_name="Central"),
            make_sector(district_name="Nyabihu", sector_name="Central"),
        ]
    )
    db_session.flush()
    assert db_session.query(Sector).count() == 2


def test_negative_slope_is_rejected(db_session, make_sector):
    db_session.add(make_sector(mean_slope_deg=Decimal("-0.01")))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_zero_slope_is_allowed(db_session, make_sector):
    db_session.add(make_sector(mean_slope_deg=Decimal(0)))
    db_session.flush()
    assert db_session.query(Sector).count() == 1


@pytest.mark.parametrize("geology", list(GeologyClass))
def test_every_geology_class_can_be_stored(db_session, geology, make_sector):
    sector = make_sector(geology_class=geology)
    db_session.add(sector)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(Sector, sector.sector_id).geology_class is geology


def test_unknown_geology_class_is_rejected_by_the_orm(db_session, make_sector):
    db_session.add(make_sector(geology_class="MARBLE"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_unknown_geology_class_is_rejected_by_the_database(db_session):
    with pytest.raises(IntegrityError):
        # Target corrected to point to valid 'sector' table structure
        db_session.execute(
            text(
                "INSERT INTO sector (sector_id, province_name, district_name, "
                "sector_name, boundary_ref, mean_slope_deg, geology_class, "
                "soil_features, land_cover_class, created_at) VALUES "
                "(:id, 'W', 'D', 'S', 'b', 10, 'MARBLE', '{}', 'Crop', "
                "'2026-01-01 00:00:00')"
            ),
            {"id": uuid.uuid4().hex},
        )
        db_session.flush()


def test_sector_relationships_are_two_way(
    db_session, make_sector, make_rainfall, make_landslide
):
    sector = make_sector()
    rainfall = make_rainfall(sector)
    landslide = make_landslide(sector)
    db_session.add(sector)
    db_session.flush()

    assert sector.rainfall_matrices == [rainfall]
    assert sector.landslide_inventory == [landslide]
    assert rainfall.sector is sector
    assert landslide.sector is sector


def test_deleting_a_sector_removes_everything_it_owns(
    db_session,
    make_sector,
    make_user,
    make_inference,
    make_feature_snapshot,
    make_alert,
    make_rainfall,
    make_landslide,
    make_incident,
    make_review,
):
    sector = make_sector()
    reviewer = make_user()
    inference = make_inference(sector)
    make_feature_snapshot(inference)
    alert = make_alert(inference)
    db_session.add_all(
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
    db_session.commit()

    db_session.delete(sector)
    db_session.commit()

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
        assert db_session.query(model).count() == 0, model.__name__
    assert db_session.query(User).count() == 1
