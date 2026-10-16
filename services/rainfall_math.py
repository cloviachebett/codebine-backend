from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator, Mapping

WINDOW_DAYS = (
    1,
    3,
    7,
    10,
    30,
)  # matches the rain_{n}day_mm columns on rainfall_matrices


def window_column(days: int) -> str:
    return f"rain_{days}day_mm"


def lookback_days(windows=WINDOW_DAYS) -> int:
    # Extra days of history needed before the first requested date.
    return max(windows) - 1


def iter_days(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def days_per_chunk(n_features: int, max_features: int) -> int:
    # How many days fit in one Earth Engine request (rows returned = sectors x days).
    return max(1, max_features // max(1, n_features))


def chunk_days(start: date, end: date, max_days: int) -> Iterator[tuple[date, date]]:
    current = start
    while current <= end:
        chunk_end = min(end, current + timedelta(days=max_days - 1))
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def compute_rolling_windows(
    daily: Mapping[date, float],
    start: date,
    end: date,
    windows=WINDOW_DAYS,
    ndigits: int = 2,  # the rainfall_matrices columns are Numeric(6, 2)
) -> tuple[list[dict], list[date]]:
    # Trailing rainfall sums that END ON (and include) each observation date.

    # A date is only produced when every day of the longest window has data; otherwise the date is skipped and reported, so a missing day never silently counts as 0 mm.

    longest = max(windows)
    rows: list[dict] = []
    skipped: list[date] = []
    for day in iter_days(start, end):
        history = [day - timedelta(days=i) for i in range(longest)]
        if any(daily.get(d) is None for d in history):
            skipped.append(day)
            continue
        row: dict = {"observation_date": day}
        for n in windows:
            row[window_column(n)] = round(
                sum(daily[day - timedelta(days=i)] for i in range(n)), ndigits
            )
        rows.append(row)
    return rows, skipped
