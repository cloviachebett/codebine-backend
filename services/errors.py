class SectorNotFoundError(LookupError):
    """A requested sector (or any sector at all) does not exist."""


class InvalidGeometryError(ValueError):
    """A sector boundary is missing, unreadable, or not a valid Polygon/MultiPolygon."""


class InvalidDateRangeError(ValueError):
    """The requested date range cannot be fetched (e.g. start after the newest CHIRPS day)."""


class ChirpsFetchError(RuntimeError):
    """Google Earth Engine / CHIRPS could not be reached or returned an error."""
