from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.errors import InvalidGeometryError
from services.geometry import validate_geometry

_FILE_CACHE: dict[tuple[str, float], Any] = {}
_GEOMETRY_TYPES = (
    "Polygon",
    "MultiPolygon",
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "GeometryCollection",
)


def _norm(value: Any) -> str:
    return " ".join(str(value).split()).casefold() if value is not None else ""


def _load_json_file(path: Path) -> Any:
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError as exc:
        raise InvalidGeometryError(
            f"boundary file not found or unreadable: {path}"
        ) from exc
    if key not in _FILE_CACHE:
        try:
            _FILE_CACHE[key] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InvalidGeometryError(
                f"boundary file is not valid GeoJSON: {path}"
            ) from exc
    return _FILE_CACHE[key]


def _pick_geometry(
    data: Any,
    sector_name: str,
    district_name: str,
    sector_property: str,
    district_property: str,
) -> Any:
    kind = data.get("type") if isinstance(data, dict) else None
    if kind in _GEOMETRY_TYPES:
        return data  # validate_geometry accepts Polygon/MultiPolygon and names anything else
    if kind == "Feature":
        return data.get("geometry")
    if kind != "FeatureCollection":
        raise InvalidGeometryError(
            "boundary must be a GeoJSON geometry, Feature or FeatureCollection"
        )

    features = data.get("features") or []

    def prop(feature, name):
        return (feature.get("properties") or {}).get(name)

    matches = [
        f for f in features if _norm(prop(f, sector_property)) == _norm(sector_name)
    ]
    if len(matches) > 1:
        in_district = [
            f
            for f in matches
            if _norm(prop(f, district_property)) == _norm(district_name)
        ]
        if not in_district:
            raise InvalidGeometryError(
                f"{len(matches)} features are named {sector_name!r} but none is in "
                f"district {district_name!r}"
            )
        matches = in_district
    if len(matches) == 1:
        return matches[0].get("geometry")
    if not matches and len(features) == 1:
        return features[0].get("geometry")  # single-sector file
    if not matches:
        raise InvalidGeometryError(
            f"no feature with {sector_property}={sector_name!r} in the boundary file"
        )
    raise InvalidGeometryError(
        f"{len(matches)} features match sector {sector_name!r} in district {district_name!r}"
    )


def resolve_boundary_geometry(
    boundary_ref: str | None,
    sector_name: str,
    district_name: str,
    base_dir: str = ".",
    sector_property: str = "ADM3_EN",
    district_property: str = "ADM2_EN",
) -> dict:
    ref = (boundary_ref or "").strip()
    if not ref:
        raise InvalidGeometryError("boundary_ref is empty")

    if ref.startswith("{"):
        try:
            data = json.loads(ref)
        except ValueError as exc:
            raise InvalidGeometryError(
                "boundary_ref holds invalid inline GeoJSON"
            ) from exc
    else:
        if ref.lower().startswith(("http://", "https://")):
            raise InvalidGeometryError(
                "remote boundary files are not supported; download the GeoJSON and "
                "point boundary_ref at the local path"
            )
        if ref.lower().startswith("file://"):
            ref = ref[7:]
        path = Path(ref).expanduser()
        if not path.is_absolute():
            path = Path(base_dir) / path
        if path.suffix.lower() not in (".geojson", ".json"):
            raise InvalidGeometryError(
                f"only GeoJSON boundary files (.geojson/.json) are supported, got {path.name!r}; "
                "convert shapefiles/GeoPackages to GeoJSON first"
            )
        data = _load_json_file(path)

    return validate_geometry(
        _pick_geometry(
            data, sector_name, district_name, sector_property, district_property
        )
    )
