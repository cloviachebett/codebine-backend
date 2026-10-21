from datetime import date

import pytest

from services.chirps_gee import CHIRPSGEEService, SectorArea


class ScriptedService(CHIRPSGEEService):
    """Real service logic with the Earth Engine call replaced by a script."""

    def __init__(self, script):
        super().__init__(ee_module=None)
        self._initialized = True
        self.script = script
        self.calls = []

    def _reduce_chunk(self, targets, start, end):
        self.calls.append(([t[0] for t in targets], start, end, targets[0][1]["type"]))
        return self.script(targets, start, end)


def area(sector_id):
    ring = [[29, -2], [29.01, -2], [29.01, -1.99], [29, -1.99], [29, -2]]
    return SectorArea(
        sector_id, {"type": "Polygon", "coordinates": [ring]}, -1.995, 29.005
    )


def every_day(value):
    def script(targets, start, end):
        days = (end - start).days + 1
        return [
            (sid, date.fromordinal(start.toordinal() + i), value)
            for sid, _ in targets
            for i in range(days)
        ]

    return script


def test_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("CHIRPS_ID", "COLLECTION/ID")
    monkeypatch.setenv("CHIRPS_SCALE_M", "1111")
    monkeypatch.setenv("GEE_MAX_FEATURES_PER_REQUEST", "2222")
    monkeypatch.setenv("GEE_PROJECT", "a-project")
    monkeypatch.setenv("GEE_PRIVATE_KEY_PATH", "/tmp/key.json")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "robot@example.com")

    service = CHIRPSGEEService(ee_module=None)

    assert service.chirps_id == "COLLECTION/ID"
    assert service.scale == 1111
    assert service.max_features == 2222
    assert service.gee_project == "a-project"
    assert service.gee_private_key_path == "/tmp/key.json"
    assert service.gee_service_account_email == "robot@example.com"


def test_requests_are_chunked_so_sectors_x_days_stay_under_the_limit(monkeypatch):
    monkeypatch.setenv("GEE_MAX_FEATURES_PER_REQUEST", "8")
    service = ScriptedService(every_day(1.5))

    result = service.fetch_daily_rainfall(
        [area(s) for s in "abcd"], date(2024, 1, 1), date(2024, 1, 5)
    )

    assert [(c[1], c[2]) for c in service.calls] == [
        (date(2024, 1, 1), date(2024, 1, 2)),
        (date(2024, 1, 3), date(2024, 1, 4)),
        (date(2024, 1, 5), date(2024, 1, 5)),
    ]
    assert all(len(v) == 5 for v in result.values())
    assert result["a"][date(2024, 1, 3)] == 1.5


def test_sector_smaller_than_a_pixel_falls_back_to_centroid_sample():
    def script(targets, start, end):
        return [
            (
                sid,
                start,
                None if (sid == "b" and geometry["type"] == "Polygon") else 4.0,
            )
            for sid, geometry in targets
        ]

    service = ScriptedService(script)
    result = service.fetch_daily_rainfall(
        [area("a"), area("b")], date(2024, 1, 1), date(2024, 1, 1)
    )

    assert result["b"][date(2024, 1, 1)] == 4.0
    assert service.unresolved == []
    assert [c[3] for c in service.calls] == ["Polygon", "Point"]
    assert service.calls[1][0] == ["b"]  # only the sector that needed it


def test_value_that_cannot_be_obtained_is_left_out_not_zero():
    service = ScriptedService(lambda targets, s, e: [(targets[0][0], s, None)])
    result = service.fetch_daily_rainfall(
        [area("a")], date(2024, 1, 1), date(2024, 1, 1)
    )

    assert result["a"] == {}
    assert service.unresolved == [("a", date(2024, 1, 1))]


def test_start_after_end_is_rejected():
    service = ScriptedService(every_day(1.0))
    with pytest.raises(ValueError):
        service.fetch_daily_rainfall([area("a")], date(2024, 2, 1), date(2024, 1, 1))


def test_latest_available_date_comes_from_the_collection():
    class FakeCollection:
        def aggregate_max(self, prop):
            assert prop == "system:time_start"
            return self

        def getInfo(self):
            return 1_711_843_200_000  # 2024-03-31T00:00:00Z

    class FakeEE:
        class EEException(Exception):
            pass

        @staticmethod
        def ImageCollection(name):
            assert name == "TEST/COLLECTION"
            return FakeCollection()

    service = CHIRPSGEEService(ee_module=FakeEE)
    service._initialized = True
    assert service.latest_available_date() == date(2024, 3, 31)


def test_earth_engine_errors_become_a_runtime_error():
    class FakeEE:
        class EEException(Exception):
            pass

        @classmethod
        def ImageCollection(cls, name):
            raise cls.EEException("quota exceeded")

    service = CHIRPSGEEService(ee_module=FakeEE)
    service._initialized = True
    with pytest.raises(RuntimeError, match="quota exceeded"):
        service.latest_available_date()


def test_missing_earth_engine_is_a_clear_error():
    service = CHIRPSGEEService(ee_module=None)
    with pytest.raises(RuntimeError, match="not installed"):
        service.fetch_daily_rainfall([area("a")], date(2024, 1, 1), date(2024, 1, 2))


def test_missing_key_file_is_an_error_not_silently_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("GEE_PRIVATE_KEY_PATH", str(tmp_path / "nope.json"))

    class FakeEE:
        class EEException(Exception):
            pass

        @staticmethod
        def Initialize(**kwargs):
            raise AssertionError("must not initialise without the key file")

    service = CHIRPSGEEService(ee_module=FakeEE)
    with pytest.raises(RuntimeError, match="key file not found"):
        service.initialize()
