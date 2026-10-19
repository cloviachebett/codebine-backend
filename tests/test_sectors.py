import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import Base, get_db
from main import app
from models._enums import GeologyClass
from models.sectors import Sector
from repositories.sectors import SectorRepository
from schemas.sectors import SectorCreate, SectorUpdate
from services.sectors import SectorService

URL = "/api/v1/sectors"
repository = SectorRepository()
service = SectorService()

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sector_payload():
    def _factory(**overrides):
        payload = {
            "province_name": "Western Province",
            "district_name": "Rubavu",
            "sector_name": "Gisenyi",
            "boundary_ref": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            "mean_slope_deg": 23.5,
            "geology_class": "GRANITE",
            "soil_features": {"texture": "clay loam", "depth_cm": 120},
            "land_cover_class": "Cropland",
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def add_sector(db_session, sector_payload):
    def _add(**overrides):
        data = sector_payload(**overrides)
        if "geology_class" in data and isinstance(data["geology_class"], str):
            data["geology_class"] = GeologyClass(data["geology_class"])
        if "mean_slope_deg" in data and not isinstance(data["mean_slope_deg"], str):
            data["mean_slope_deg"] = float(data["mean_slope_deg"])
        sector = Sector(**data)
        db_session.add(sector)
        db_session.commit()
        db_session.refresh(sector)
        return sector

    return _add


def test_repository_get_returns_sector_or_none(db_session, add_sector):
    sector = add_sector(district_name="Rubavu", sector_name="Nyamyumba")

    assert repository.get(db_session, sector.sector_id).sector_name == "Nyamyumba"
    assert repository.get(db_session, uuid.uuid4()) is None


def test_repository_get_all_filters_and_orders(db_session, add_sector):
    add_sector(district_name="Rubavu", sector_name="Kanama")
    add_sector(district_name="Rubavu", sector_name="Gisenyi")
    add_sector(district_name="Karongi", sector_name="Bwishyura")

    all_rows = repository.get_all(db_session)
    assert [row.sector_name for row in all_rows] == [
        "Bwishyura",
        "Gisenyi",
        "Kanama",
    ]

    rubavu = repository.get_all(db_session, district_name="Rubavu")
    assert [row.sector_name for row in rubavu] == ["Gisenyi", "Kanama"]


def test_repository_get_by_location_matches_district_and_name(db_session, add_sector):
    add_sector(district_name="Rubavu", sector_name="Nyamyumba")
    add_sector(district_name="Karongi", sector_name="Nyamyumba")

    found = repository.get_by_location(db_session, "Karongi", "Nyamyumba")
    assert found.district_name == "Karongi"
    assert repository.get_by_location(db_session, "Karongi", "Missing") is None


def test_repository_delete_and_update(db_session, add_sector):
    sector = add_sector(district_name="Rubavu", sector_name="Gisenyi")
    sector.land_cover_class = "Forest"
    updated = repository.update(db_session, sector)
    assert updated.land_cover_class == "Forest"

    repository.delete(db_session, sector)
    assert repository.get(db_session, sector.sector_id) is None
    assert db_session.query(Sector).count() == 0


def test_service_create_sector_saves_and_validates(db_session, sector_payload):
    result = service.create_sector(db_session, SectorCreate(**sector_payload()))

    assert result.sector_name == "Gisenyi"
    assert result.sector_id is not None
    assert db_session.query(Sector).count() == 1


def test_service_create_rejects_duplicate_sector_name_in_same_district(
    db_session, sector_payload
):
    payload = sector_payload(district_name="Rubavu", sector_name="Gisenyi")
    service.create_sector(db_session, SectorCreate(**payload))

    with pytest.raises(Exception):
        service.create_sector(db_session, SectorCreate(**payload))


def test_service_allows_same_sector_name_in_other_district(db_session, sector_payload):
    service.create_sector(
        db_session,
        SectorCreate(**sector_payload(district_name="Rubavu", sector_name="Gisenyi")),
    )
    second = service.create_sector(
        db_session,
        SectorCreate(**sector_payload(district_name="Karongi", sector_name="Gisenyi")),
    )
    assert second.district_name == "Karongi"


def test_service_get_sector_unknown_id_raises_404(db_session):
    with pytest.raises(Exception):
        service.get_sector(db_session, uuid.uuid4())


def test_service_get_all_sectors_filters_by_district(db_session, add_sector):
    add_sector(district_name="Rubavu", sector_name="A")
    add_sector(district_name="Rubavu", sector_name="B")
    add_sector(district_name="Karongi", sector_name="C")

    assert len(service.get_all_sectors(db_session)) == 3
    assert len(service.get_all_sectors(db_session, district_name="Rubavu")) == 2


def test_service_update_sector_updates_only_sent_fields(db_session, add_sector):
    sector = add_sector(land_cover_class="Cropland", mean_slope_deg=18.5)

    updated = service.update_sector(
        db_session,
        sector.sector_id,
        SectorUpdate(land_cover_class="Forest"),
    )

    assert updated.land_cover_class == "Forest"
    assert updated.mean_slope_deg == 18.5


def test_service_update_rejects_duplicate_name(db_session, add_sector):
    add_sector(district_name="Rubavu", sector_name="Gisenyi")
    other = add_sector(district_name="Rubavu", sector_name="Kanama")

    with pytest.raises(Exception):
        service.update_sector(
            db_session,
            other.sector_id,
            SectorUpdate(sector_name="Gisenyi"),
        )


def test_service_delete_sector_success(db_session, add_sector):
    sector = add_sector(district_name="Rubavu", sector_name="Gisenyi")

    result = service.delete_sector(db_session, sector.sector_id)

    assert result == {"detail": "Sector deleted successfully"}
    assert db_session.query(Sector).count() == 0


def test_service_delete_unknown_sector_raises_404(db_session):
    with pytest.raises(Exception):
        service.delete_sector(db_session, uuid.uuid4())


def test_api_create_and_get_sector(client, sector_payload):
    response = client.post(URL, json=sector_payload())
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["district_name"] == "Rubavu"
    assert data["sector_name"] == "Gisenyi"
    assert data["geology_class"] == "GRANITE"

    fetched = client.get(f"{URL}/{data['sector_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["sector_name"] == "Gisenyi"


def test_api_duplicate_sector_returns_409(client, sector_payload):
    payload = sector_payload(district_name="Rubavu", sector_name="Gisenyi")
    assert client.post(URL, json=payload).status_code == 201
    assert client.post(URL, json=payload).status_code == 409


def test_api_list_returns_sector_rows(client, db_session, sector_payload):
    db_session.add(
        Sector(
            sector_id=uuid.uuid4(),
            province_name="Western Province",
            district_name="Karongi",
            sector_name="Bwishyura",
            boundary_ref="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            mean_slope_deg=12.3,
            geology_class=GeologyClass.GRANITE,
            soil_features={"clay_percent": 30.1},
            land_cover_class="Forest",
        )
    )
    db_session.commit()

    response = client.get(URL)
    assert response.status_code == 200
    assert any(item["sector_name"] == "Bwishyura" for item in response.json())


def test_api_patch_updates_sector(client, sector_payload):
    created = client.post(URL, json=sector_payload()).json()

    response = client.patch(
        f"{URL}/{created['sector_id']}",
        json={"land_cover_class": "Forest", "mean_slope_deg": 19.2},
    )

    assert response.status_code == 200
    assert response.json()["land_cover_class"] == "Forest"
    assert float(response.json()["mean_slope_deg"]) == 19.2


def test_api_delete_sector(client, sector_payload):
    created = client.post(URL, json=sector_payload()).json()

    delete_response = client.delete(f"{URL}/{created['sector_id']}")
    assert delete_response.status_code == 200

    get_response = client.get(f"{URL}/{created['sector_id']}")
    assert get_response.status_code == 404


@pytest.mark.parametrize(
    "missing",
    ["province_name", "district_name", "sector_name"],
)
def test_api_missing_required_field_is_422(client, sector_payload, missing):
    payload = sector_payload()
    del payload[missing]
    response = client.post(URL, json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_value",
    [
        {"mean_slope_deg": -1},
        {"mean_slope_deg": 91},
        {"sector_name": ""},
        {"sector_name": "x" * 51},
        {"geology_class": "NOT_A_REAL_GEOLOGY"},
    ],
)
def test_api_invalid_values_are_rejected(client, sector_payload, bad_value):
    payload = sector_payload()
    payload.update(bad_value)
    assert client.post(URL, json=payload).status_code == 422


def test_api_unknown_id_returns_404(client):
    assert client.get(f"{URL}/{uuid.uuid4()}").status_code == 404
    assert (
        client.patch(
            f"{URL}/{uuid.uuid4()}", json={"land_cover_class": "Forest"}
        ).status_code
        == 404
    )
    assert client.delete(f"{URL}/{uuid.uuid4()}").status_code == 404


def test_api_get_list_supports_filter_and_paging(client, sector_payload):
    client.post(URL, json=sector_payload(district_name="Rubavu", sector_name="A"))
    client.post(URL, json=sector_payload(district_name="Rubavu", sector_name="B"))
    client.post(URL, json=sector_payload(district_name="Karongi", sector_name="C"))

    all_rows = client.get(URL)
    assert len(all_rows.json()) == 3

    filtered = client.get(URL, params={"district_name": "Rubavu"})
    assert [item["sector_name"] for item in filtered.json()] == ["A", "B"]

    limited = client.get(URL, params={"limit": 1})
    assert len(limited.json()) == 1
    assert client.get(URL, params={"limit": 0}).status_code == 422
    assert client.get(URL, params={"skip": -1}).status_code == 422
