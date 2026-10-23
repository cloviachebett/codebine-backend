# Tests for RainfallService (CHIRPS sync, rolling windows, upsert, reads).

import json
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException

from models._enums import ProcessingStatus
from models.dataset_metadata import DatasetMetadata
from models.rainfall_matrices import RainfallMatrix
from models.system_audit_logs import SystemAuditLog
from repositories.rainfall_matrices import utc_date
from services.rainfall_matrices import RainfallService


def rows_by_day(db, sector):
    rows = (
        db.query(RainfallMatrix)
        .filter(RainfallMatrix.sector_id == sector.sector_id)
        .all()
    )
    return {utc_date(r.observation_time): r for r in rows}


def make_service(settings, chirps):
    return RainfallService(settings=settings, chirps=chirps)


def test_sync_stores_rolling_windows_per_sector(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    summary = make_service(rainfall_settings, fake_chirps()).run_sync(
        db_session, start=date(2024, 3, 10), end=date(2024, 3, 20)
    )

    rows = rows_by_day(db_session, sector)
    assert summary["rows_inserted"] == 11 and summary["rows_updated"] == 0
    assert float(rows[date(2024, 3, 10)].rain_1day_mm) == 50.0
    assert float(rows[date(2024, 3, 12)].rain_3day_mm) == 50.0
    assert float(rows[date(2024, 3, 13)].rain_3day_mm) == 0.0
    assert float(rows[date(2024, 3, 16)].rain_7day_mm) == 50.0
    assert float(rows[date(2024, 3, 17)].rain_7day_mm) == 0.0
    assert float(rows[date(2024, 3, 19)].rain_10day_mm) == 50.0
    assert float(rows[date(2024, 3, 20)].rain_10day_mm) == 0.0
    assert float(rows[date(2024, 3, 20)].rain_30day_mm) == 50.0


def test_short_sync_still_gets_correct_30_day_totals(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    # Regression: a 3-day sync must still see the 29 days before it (history is fetched).
    sector = add_sector()
    chirps = fake_chirps()
    make_service(rainfall_settings, chirps).run_sync(
        db_session, start=date(2024, 3, 12), end=date(2024, 3, 14)
    )

    assert chirps.calls[0]["start"] == date(
        2024, 2, 12
    )  # 29 days before the first date
    rows = rows_by_day(db_session, sector)
    assert (
        float(rows[date(2024, 3, 12)].rain_30day_mm) == 50.0
    )  # includes the 03-10 spike


def test_sync_twice_updates_in_place_without_duplicates(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    make_service(rainfall_settings, fake_chirps()).run_sync(
        db_session, start=date(2024, 3, 10), end=date(2024, 3, 20)
    )
    summary = make_service(rainfall_settings, fake_chirps(spike_mm=80.0)).run_sync(
        db_session, start=date(2024, 3, 10), end=date(2024, 3, 20)
    )

    rows = rows_by_day(db_session, sector)
    assert summary["rows_inserted"] == 0 and summary["rows_updated"] == 11
    assert len(rows) == 11
    assert float(rows[date(2024, 3, 10)].rain_1day_mm) == 80.0


def test_sync_only_touches_the_requested_dates(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    make_service(rainfall_settings, fake_chirps()).run_sync(
        db_session, start=date(2024, 3, 10), end=date(2024, 3, 20)
    )
    make_service(rainfall_settings, fake_chirps(spike_mm=80.0)).run_sync(
        db_session, start=date(2024, 3, 18), end=date(2024, 3, 25)
    )

    rows = rows_by_day(db_session, sector)
    assert len(rows) == 16  # 3/10 .. 3/25, nothing deleted
    assert (
        float(rows[date(2024, 3, 10)].rain_1day_mm) == 50.0
    )  # earlier history untouched
    assert (
        float(rows[date(2024, 3, 20)].rain_30day_mm) == 80.0
    )  # overlapping day refreshed


def test_each_sector_gets_its_own_rows(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    a, b = add_sector(), add_sector()
    make_service(rainfall_settings, fake_chirps()).run_sync(db_session)

    assert len(rows_by_day(db_session, a)) == 3
    assert len(rows_by_day(db_session, b)) == 3


def test_sector_ids_limit_the_sync(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    a, b = add_sector(), add_sector()
    summary = make_service(rainfall_settings, fake_chirps()).run_sync(
        db_session, sector_ids=[a.sector_id]
    )

    assert summary["sectors_synced"] == 1
    assert len(rows_by_day(db_session, a)) == 3 and rows_by_day(db_session, b) == {}


def test_default_range_is_the_lookback_window_ending_at_latest_chirps(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    summary = make_service(rainfall_settings, fake_chirps()).run_sync(db_session)

    assert summary["start_date"] == "2024-03-29" and summary["end_date"] == "2024-03-31"
    assert set(rows_by_day(db_session, sector)) == {
        date(2024, 3, 29),
        date(2024, 3, 30),
        date(2024, 3, 31),
    }


def test_end_date_beyond_chirps_is_clamped_not_invented(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    add_sector()
    summary = make_service(rainfall_settings, fake_chirps()).run_sync(
        db_session, start=date(2024, 3, 25), end=date(2024, 4, 30)
    )
    assert summary["end_date"] == "2024-03-31"
    assert summary["clamped_to_latest_available"] is True


def test_start_after_latest_chirps_is_an_error(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    add_sector()
    with pytest.raises(ValueError):
        make_service(rainfall_settings, fake_chirps()).run_sync(
            db_session, start=date(2024, 4, 5), end=date(2024, 4, 6)
        )


def test_missing_chirps_days_produce_no_rows_rather_than_zeros(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    summary = make_service(
        rainfall_settings, fake_chirps(missing={date(2024, 3, 5)})
    ).run_sync(db_session, start=date(2024, 3, 10), end=date(2024, 3, 20))
    assert rows_by_day(db_session, sector) == {}
    assert summary["days_skipped_incomplete"] == 11
    assert summary["sectors_with_missing_data"] == [str(sector.sector_id)]


def test_unknown_sector_and_empty_database_raise_not_found(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    service = make_service(rainfall_settings, fake_chirps())
    with pytest.raises(LookupError):
        service.run_sync(db_session)  # no sectors yet
    add_sector()
    with pytest.raises(LookupError):
        service.run_sync(db_session, sector_ids=[uuid4()])


def test_invalid_geometry_is_reported_not_replaced_by_a_province_polygon(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    add_sector(boundary_ref='{"type": "Point", "coordinates": [29.0, -2.9]}')
    chirps = fake_chirps()
    with pytest.raises(ValueError, match="must be coordinates"):
        make_service(rainfall_settings, chirps).run_sync(db_session)
    assert chirps.calls == []  # nothing was fetched


def test_boundary_ref_can_be_a_geojson_collection_shared_by_many_sectors(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    a_poly = {
        "type": "Polygon",
        "coordinates": [
            [[29.0, -2.0], [29.1, -2.0], [29.1, -1.9], [29.0, -1.9], [29.0, -2.0]]
        ],
    }
    b_poly = {
        "type": "Polygon",
        "coordinates": [
            [[30.0, -2.0], [30.1, -2.0], [30.1, -1.9], [30.0, -1.9], [30.0, -2.0]]
        ],
    }
    shared = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ADM3_EN": "Gisenyi", "ADM2_EN": "Rubavu"},
                    "geometry": a_poly,
                },
                {
                    "type": "Feature",
                    "properties": {"ADM3_EN": "Kanama", "ADM2_EN": "Rubavu"},
                    "geometry": b_poly,
                },
            ],
        }
    )
    gisenyi = add_sector(
        sector_name="Gisenyi",
        district_name="Rubavu",
        boundary_ref=shared,
    )
    kanama = add_sector(
        sector_name="Kanama",
        district_name="Rubavu",
        boundary_ref=shared,
    )

    chirps = fake_chirps()
    make_service(rainfall_settings, chirps).run_sync(db_session)

    geometries = {a.sector_id: a.geometry for a in chirps.calls[0]["areas"]}
    assert (
        geometries[str(gisenyi.sector_id)] == a_poly
    )  # each sector gets its OWN polygon
    assert geometries[str(kanama.sector_id)] == b_poly


def test_multipolygon_sector_is_synced(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    ring = [[29, -2], [29.1, -2], [29.1, -1.9], [29, -1.9], [29, -2]]
    multi = {"type": "MultiPolygon", "coordinates": [[ring], [ring]]}
    sector = add_sector(boundary_ref=json.dumps(multi))
    make_service(rainfall_settings, fake_chirps()).run_sync(db_session)
    assert len(rows_by_day(db_session, sector)) == 3


def test_successful_sync_records_dataset_and_audit_log(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    make_service(rainfall_settings, fake_chirps()).run_sync(db_session)

    dataset = db_session.query(DatasetMetadata).one()
    assert dataset.processing_status == ProcessingStatus.READY
    assert dataset.last_processed_at is not None
    assert all(
        r.dataset_id == dataset.dataset_id
        for r in rows_by_day(db_session, sector).values()
    )
    assert db_session.query(SystemAuditLog).one().action_type == "RAINFALL_SYNC_SUCCESS"


def test_failed_fetch_marks_dataset_failed_and_reraises(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    add_sector()
    with pytest.raises(RuntimeError):
        make_service(rainfall_settings, fake_chirps(fail=True)).run_sync(db_session)

    assert (
        db_session.query(DatasetMetadata).one().processing_status
        == ProcessingStatus.FAILED
    )
    assert db_session.query(SystemAuditLog).one().action_type == "RAINFALL_SYNC_FAILED"
    assert db_session.query(RainfallMatrix).count() == 0


def test_status_and_sector_reads(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    sector = add_sector()
    service = make_service(rainfall_settings, fake_chirps())
    assert service.get_status(db_session)["stored_rows"] == 0

    service.run_sync(db_session)
    status = service.get_status(db_session)
    assert status["stored_rows"] == 3 and status["latest_stored_date"] == "2024-03-31"
    assert status["dataset_status"] == "READY"
    assert (
        service.get_status(db_session, include_chirps=True)["chirps_latest_available"]
        == "2024-03-31"
    )

    records = service.get_sector_matrix(db_session, sector.sector_id)
    assert [utc_date(r.observation_time) for r in records] == [
        date(2024, 3, 29),
        date(2024, 3, 30),
        date(2024, 3, 31),
    ]  # oldest first
    assert (
        len(
            service.get_sector_matrix(
                db_session, sector.sector_id, start=date(2024, 3, 30)
            )
        )
        == 2
    )
    assert (
        len(
            service.get_sector_matrix(
                db_session, sector.sector_id, end=date(2024, 3, 29)
            )
        )
        == 1
    )
    with pytest.raises(HTTPException) as excinfo:
        service.get_sector_matrix(db_session, uuid4())
    assert excinfo.value.status_code == 404


def test_list_matrices_filters_and_orders_newest_first(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    a, _b = add_sector(), add_sector()
    service = make_service(rainfall_settings, fake_chirps())
    service.run_sync(db_session)

    everything = service.get_all_matrices(db_session)
    assert len(everything) == 6
    assert everything[0].observation_time >= everything[-1].observation_time
    assert len(service.get_all_matrices(db_session, sector_id=a.sector_id)) == 3
    assert len(service.get_all_matrices(db_session, limit=2)) == 2


@pytest.mark.parametrize(
    "build, expected",
    [
        (
            lambda add_sector, fake_chirps: (
                None,
                fake_chirps(),
                {"sector_ids": [uuid4()]},
            ),
            404,
        ),  # unknown sector
        (
            lambda add_sector, fake_chirps: (
                add_sector(boundary_ref='{"type": "Point", "coordinates": [29, -2]}'),
                fake_chirps(),
                {},
            ),
            400,
        ),
        (
            lambda add_sector, fake_chirps: (
                add_sector(),
                fake_chirps(),
                {"start": date(2024, 4, 5), "end": date(2024, 4, 6)},
            ),
            400,
        ),
        (
            lambda add_sector, fake_chirps: (
                add_sector(),
                fake_chirps(),
                {"start": date(2024, 3, 10), "end": date(2024, 3, 1)},
            ),
            400,
        ),
        (
            lambda add_sector, fake_chirps: (add_sector(), fake_chirps(fail=True), {}),
            502,
        ),
    ],
)
def test_sync_rainfall_turns_errors_into_http_errors(
    db_session, rainfall_settings, add_sector, fake_chirps, build, expected
):
    _, chirps, kwargs = build(add_sector, fake_chirps)
    service = make_service(rainfall_settings, chirps)

    with pytest.raises(HTTPException) as excinfo:
        service.sync_rainfall(db_session, **kwargs)
    assert excinfo.value.status_code == expected


def test_sync_rainfall_success_returns_the_summary(
    db_session, rainfall_settings, add_sector, fake_chirps
):
    add_sector()
    summary = make_service(rainfall_settings, fake_chirps()).sync_rainfall(db_session)
    assert summary["rows_inserted"] == 3


def test_status_reports_chirps_failure_as_502(
    db_session, rainfall_settings, fake_chirps
):
    class Broken(fake_chirps):
        def latest_available_date(self):
            raise RuntimeError("down")

    with pytest.raises(HTTPException) as excinfo:
        make_service(rainfall_settings, Broken()).get_status(
            db_session, include_chirps=True
        )
    assert excinfo.value.status_code == 502
