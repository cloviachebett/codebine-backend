from __future__ import annotations

import json
from typing import Any

from services.geometry import validate_geometry


def _norm(value: Any) -> str:
    return " ".join(str(value).split()).casefold() if value is not None else ""


def _pick_geometry(
    data: Any,
    sector_name: str,
    district_name: str,
    sector_property: str,
    district_property: str,
) -> Any:
    if isinstance(data, list):
        data = {
            "type": "Polygon",
            "coordinates": [data],
        }

    kind = data.get("type") if isinstance(data, dict) else None

    if kind in ("Polygon", "MultiPolygon"):
        return data

    if kind == "Feature":
        return data.get("geometry")

    if kind != "FeatureCollection":
        raise ValueError(
            "boundary must be coordinates, a GeoJSON geometry, Feature or FeatureCollection"
        )

    features = data.get("features") or []

    def prop(feature: dict, name: str) -> Any:
        return (feature.get("properties") or {}).get(name)

    matches = [
        feature
        for feature in features
        if _norm(prop(feature, sector_property)) == _norm(sector_name)
    ]

    if len(matches) > 1:
        matches = [
            feature
            for feature in matches
            if _norm(prop(feature, district_property)) == _norm(district_name)
        ]

    if len(matches) == 1:
        return matches[0].get("geometry")

    if not matches:
        raise ValueError(
            f"no feature with {sector_property}={sector_name!r} in the boundary data"
        )

    raise ValueError(
        f"{len(matches)} features match sector {sector_name!r} "
        f"in district {district_name!r}"
    )


def resolve_boundary_geometry(
    boundary_ref: str | None,
    sector_name: str,
    district_name: str,
    sector_property: str = "ADM3_EN",
    district_property: str = "ADM2_EN",
) -> dict:
    ref = (boundary_ref or "").strip()

    if not ref:
        raise ValueError("boundary_ref is empty")

    try:
        data = json.loads(ref)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "boundary_ref must contain valid JSON coordinates or GeoJSON"
        ) from exc

    geometry = _pick_geometry(
        data,
        sector_name,
        district_name,
        sector_property,
        district_property,
    )

    return validate_geometry(geometry)
