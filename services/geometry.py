from __future__ import annotations

from typing import Any


def _validate_position(pos: Any) -> None:
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        raise ValueError("each position must be [lon, lat]")

    lon, lat = pos[0], pos[1]

    for value in (lon, lat):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("coordinates must be numbers")

    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError("coordinates are outside lon/lat range")


def _validate_polygon(rings: Any) -> None:
    if not isinstance(rings, (list, tuple)) or not rings:
        raise ValueError("polygon needs at least one ring")

    for ring in rings:
        if not isinstance(ring, (list, tuple)) or len(ring) < 4:
            raise ValueError("a polygon ring needs at least 4 positions")

        for pos in ring:
            _validate_position(pos)

        if list(ring[0][:2]) != list(ring[-1][:2]):
            raise ValueError("a polygon ring must be closed")


def validate_geometry(geojson: Any) -> dict:
    """Return the geometry unchanged if it is a valid Polygon/MultiPolygon."""
    if not isinstance(geojson, dict):
        raise ValueError("geometry must be a GeoJSON object")

    gtype = geojson.get("type")
    coords = geojson.get("coordinates")

    if gtype == "Polygon":
        _validate_polygon(coords)

    elif gtype == "MultiPolygon":
        if not isinstance(coords, (list, tuple)) or not coords:
            raise ValueError("MultiPolygon needs at least one polygon")

        for polygon in coords:
            _validate_polygon(polygon)

    else:
        raise ValueError(
            f"unsupported geometry type {gtype!r}; expected Polygon or MultiPolygon"
        )

    return geojson


def _ring_area_centroid(ring) -> tuple[float, float, float]:
    area = cx = cy = 0.0

    for (x0, y0), (x1, y1) in zip(
        (p[:2] for p in ring),
        (p[:2] for p in ring[1:]),
    ):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    area /= 2.0

    if area == 0:
        return 0.0, 0.0, 0.0

    return area, cx / (6.0 * area), cy / (6.0 * area)


def compute_centroid(geojson: dict) -> tuple[float, float]:
    """Return the area-weighted centroid of outer rings as (latitude, longitude)."""
    validate_geometry(geojson)

    polygons = (
        [geojson["coordinates"]]
        if geojson["type"] == "Polygon"
        else geojson["coordinates"]
    )

    total = sx = sy = 0.0

    for polygon in polygons:
        area, cx, cy = _ring_area_centroid(polygon[0])
        weight = abs(area)
        total += weight
        sx += cx * weight
        sy += cy * weight

    if total == 0:
        points = [p for poly in polygons for p in poly[0][:-1]]

        return (
            sum(p[1] for p in points) / len(points),
            sum(p[0] for p in points) / len(points),
        )

    return sy / total, sx / total
