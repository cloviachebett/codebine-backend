# HTTP-level tests for /rainfall.

from datetime import datetime, timezone
from decimal import Decimal

import pytest

import services.rainfall_matrices as rainfall_module
from services.errors import (
    ChirpsFetchError,
    InvalidDateRangeError,
    InvalidGeometryError,
    SectorNotFoundError,
)
from services.rainfall_matrices import RainfallService


def add_row(db, sector, day=1, **values):
    from models.rainfall_matrices import RainfallMatrix

    row = RainfallMatrix(
        sector_id=sector.sector_id,
        observation_time=datetime(2026, 4, day, tzinfo=timezone.utc),
        rain_1day_mm=Decimal("10.50"),
        rain_3day_mm=Decimal("20.00"),
        rain_7day_mm=Decimal("30.00"),
        rain_10day_mm=Decimal("40.00"),
        rain_30day_mm=Decimal("50.00"),
        **values,
    )
    db.add(row)
    db.commit()
    return row


def test_list_matrices_serialises_uuids_and_numbers(client, db_session, add_sector):
    sector = add_sector()
    row = add_row(db_session, sector)

    response = client.get("/rainfall/matrices")

    assert response.status_code == 200
    body = response.json()[0]
    assert body["rainfall_id"] == str(row.rainfall_id)
    assert body["sector_id"] == str(sector.sector_id)
    assert body["rain_1day_mm"] == 10.5 and body["rain_30day_mm"] == 50.0
    assert body["dataset_id"] is None


def test_sector_rainfall_returns_rows_oldest_first(client, db_session, add_sector):
    sector = add_sector()
    add_row(db_session, sector, day=2)
    add_row(db_session, sector, day=1)

    response = client.get(f"/rainfall/sectors/{sector.sector_id}")

    assert response.status_code == 200
    days = [r["observation_time"][:10] for r in response.json()]
    assert days == ["2026-04-01", "2026-04-02"]


def test_sector_rainfall_date_filter(client, db_session, add_sector):
    sector = add_sector()
    for day in (1, 2, 3):
        add_row(db_session, sector, day=day)

    response = client.get(
        f"/rainfall/sectors/{sector.sector_id}?start_date=2026-04-02&end_date=2026-04-02"
    )
    assert [r["observation_time"][:10] for r in response.json()] == ["2026-04-02"]


def test_sector_with_no_rows_is_an_empty_list_unknown_sector_is_404(client, add_sector):
    sector = add_sector()
    assert client.get(f"/rainfall/sectors/{sector.sector_id}").json() == []
    assert (
        client.get("/rainfall/sectors/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )


def test_invalid_sector_id_is_422_not_500(client):
    assert client.get("/rainfall/sectors/not-a-uuid").status_code == 422
    assert client.post("/rainfall/sync?sector_id=not-a-uuid").status_code == 422


@pytest.mark.parametrize(
    "error, expected",
    [
        (SectorNotFoundError("no such sector"), 404),
        (InvalidGeometryError("bad boundary"), 400),
        (InvalidDateRangeError("bad range"), 400),
        (ChirpsFetchError("gee down"), 502),
    ],
)
def test_sync_maps_service_errors_to_http_codes(client, monkeypatch, error, expected):
    def boom(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(RainfallService, "run_sync", boom)
    response = client.post("/rainfall/sync")
    assert response.status_code == expected
    assert str(error) in response.json()["detail"]


def test_sync_rejects_start_after_end(client):
    response = client.post("/rainfall/sync?start_date=2024-03-10&end_date=2024-03-01")
    assert response.status_code == 400


def test_sync_end_to_end_with_fake_chirps(client, add_sector, monkeypatch, fake_chirps):
    sector = add_sector()
    monkeypatch.setattr(
        rainfall_module, "CHIRPSGEEService", lambda **kwargs: fake_chirps()
    )

    response = client.post(
        f"/rainfall/sync?sector_id={sector.sector_id}&start_date=2024-03-10&end_date=2024-03-12"
    )
    assert response.status_code == 200
    summary = response.json()
    assert (
        summary["rows_inserted"] == 3
        and summary["chirps_latest_available"] == "2024-03-31"
    )

    rows = client.get(f"/rainfall/sectors/{sector.sector_id}").json()
    assert [r["observation_time"][:10] for r in rows] == [
        "2024-03-10",
        "2024-03-11",
        "2024-03-12",
    ]
    assert rows[0]["rain_1day_mm"] == 50.0 and rows[0]["rain_30day_mm"] == 50.0
    assert rows[0]["dataset_id"] is not None


def test_status_endpoint(client):
    response = client.get("/rainfall/status")
    assert response.status_code == 200
    assert response.json()["stored_rows"] == 0


def test_manual_rainfall_insert_and_province_endpoints_are_gone(client):
    assert client.post("/rainfall/matrices", json={}).status_code == 405
    assert client.post("/rainfall/sync-western-province").status_code == 404
    assert client.get("/rainfall/western-province-summary").status_code == 404
