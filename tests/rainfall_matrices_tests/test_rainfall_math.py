from datetime import date

from services.rainfall_math import (
    chunk_days,
    compute_rolling_windows,
    days_per_chunk,
    iter_days,
    lookback_days,
)


def series(start, end, fn):
    return {d: fn(d) for d in iter_days(start, end)}


def test_windows_are_trailing_sums_ending_on_the_date():
    spike = date(2024, 3, 10)
    daily = series(
        date(2024, 2, 1), date(2024, 3, 31), lambda d: 50.0 if d == spike else 0.0
    )

    rows, skipped = compute_rolling_windows(daily, date(2024, 3, 10), date(2024, 3, 20))
    by_day = {r["observation_date"]: r for r in rows}

    assert skipped == []
    assert by_day[date(2024, 3, 10)]["rain_1day_mm"] == 50.0
    assert by_day[date(2024, 3, 11)]["rain_1day_mm"] == 0.0
    assert by_day[date(2024, 3, 12)]["rain_3day_mm"] == 50.0  # days 10-12
    assert by_day[date(2024, 3, 13)]["rain_3day_mm"] == 0.0  # days 11-13
    assert by_day[date(2024, 3, 16)]["rain_7day_mm"] == 50.0  # days 10-16
    assert by_day[date(2024, 3, 17)]["rain_7day_mm"] == 0.0  # days 11-17
    assert by_day[date(2024, 3, 19)]["rain_10day_mm"] == 50.0  # days 10-19
    assert by_day[date(2024, 3, 20)]["rain_10day_mm"] == 0.0  # days 11-20
    assert by_day[date(2024, 3, 20)]["rain_30day_mm"] == 50.0


def test_constant_rain_gives_window_length_times_rate():
    daily = series(date(2024, 1, 1), date(2024, 2, 29), lambda d: 2.0)
    row = compute_rolling_windows(daily, date(2024, 2, 29), date(2024, 2, 29))[0][0]
    assert (row["rain_1day_mm"], row["rain_3day_mm"], row["rain_7day_mm"]) == (
        2.0,
        6.0,
        14.0,
    )
    assert (row["rain_10day_mm"], row["rain_30day_mm"]) == (20.0, 60.0)


def test_short_history_is_skipped_not_treated_as_zero():
    # Only 3 days of data: the old behaviour stored rain_30day_mm = 30 instead of 300.
    daily = series(date(2026, 1, 1), date(2026, 1, 3), lambda d: 10.0)
    rows, skipped = compute_rolling_windows(daily, date(2026, 1, 1), date(2026, 1, 3))
    assert rows == []
    assert len(skipped) == 3


def test_missing_day_skips_dates_whose_window_contains_it():
    daily = series(date(2024, 1, 1), date(2024, 2, 29), lambda d: 1.0)
    del daily[date(2024, 2, 10)]
    rows, skipped = compute_rolling_windows(daily, date(2024, 2, 8), date(2024, 2, 29))
    assert [r["observation_date"] for r in rows] == [date(2024, 2, 8), date(2024, 2, 9)]
    assert len(skipped) == 20


def test_none_value_is_treated_as_missing():
    daily = series(date(2024, 1, 1), date(2024, 2, 29), lambda d: 1.0)
    daily[date(2024, 2, 29)] = None
    rows, skipped = compute_rolling_windows(daily, date(2024, 2, 29), date(2024, 2, 29))
    assert rows == [] and skipped == [date(2024, 2, 29)]


def test_sums_are_rounded_to_the_column_precision():
    daily = series(date(2024, 1, 1), date(2024, 1, 30), lambda d: 0.123456)
    row = compute_rolling_windows(daily, date(2024, 1, 30), date(2024, 1, 30))[0][0]
    assert row["rain_1day_mm"] == 0.12
    assert row["rain_30day_mm"] == 3.7


def test_lookback_and_chunking():
    assert lookback_days() == 29
    assert days_per_chunk(400, 4000) == 10
    assert days_per_chunk(10_000, 4000) == 1  # never zero
    assert list(chunk_days(date(2024, 1, 1), date(2024, 1, 10), 4)) == [
        (date(2024, 1, 1), date(2024, 1, 4)),
        (date(2024, 1, 5), date(2024, 1, 8)),
        (date(2024, 1, 9), date(2024, 1, 10)),
    ]
