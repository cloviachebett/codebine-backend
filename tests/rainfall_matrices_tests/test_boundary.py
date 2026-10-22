import json

import pytest

from services.boundary import resolve_boundary_geometry


def poly(lon, lat, size=0.1):
    ring = [
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def feature(sector, district, geometry):
    return {
        "type": "Feature",
        "properties": {"ADM3_EN": sector, "ADM2_EN": district},
        "geometry": geometry,
    }


def test_inline_geojson_string():
    geometry = poly(29, -2)
    assert resolve_boundary_geometry(json.dumps(geometry), "A", "B") == geometry


def test_feature_collection_matches_by_sector_name():
    a, b = poly(29, -2), poly(30, -2)
    data = {
        "type": "FeatureCollection",
        "features": [
            feature("Gisenyi", "Rubavu", a),
            feature("Kanama", "Rubavu", b),
        ],
    }

    ref = json.dumps(data)

    assert resolve_boundary_geometry(ref, "Kanama", "Rubavu") == b
    assert resolve_boundary_geometry(ref, "  gisenyi ", "rubavu") == a


def test_same_sector_name_in_two_districts_needs_the_district():
    a, b = poly(29, -2), poly(30, -2)
    data = {
        "type": "FeatureCollection",
        "features": [
            feature("Nyamyumba", "Rubavu", a),
            feature("Nyamyumba", "Karongi", b),
        ],
    }

    ref = json.dumps(data)

    assert resolve_boundary_geometry(ref, "Nyamyumba", "Karongi") == b

    with pytest.raises(ValueError, match="no feature"):
        resolve_boundary_geometry(ref, "Nyamyumba", "Unknown District")


def test_single_feature_collection_still_needs_a_name_match():
    geometry = poly(29, -2)
    data = {
        "type": "FeatureCollection",
        "features": [feature("Whatever", "Elsewhere", geometry)],
    }

    assert (
        resolve_boundary_geometry(json.dumps(data), "Whatever", "Elsewhere") == geometry
    )

    with pytest.raises(ValueError, match="no feature"):
        resolve_boundary_geometry(json.dumps(data), "Other", "Other")


def test_bare_coordinate_list_is_treated_as_a_polygon():
    ring = [[29, -2], [30, -2], [30, -1], [29, -1], [29, -2]]
    assert resolve_boundary_geometry(json.dumps(ring), "A", "B") == {
        "type": "Polygon",
        "coordinates": [ring],
    }


def test_geojson_feature_is_unwrapped():
    geometry = poly(29, -2)
    data = feature("Gisenyi", "Rubavu", geometry)

    assert resolve_boundary_geometry(json.dumps(data), "Gisenyi", "Rubavu") == geometry


def test_no_matching_feature_is_an_error():
    data = {
        "type": "FeatureCollection",
        "features": [
            feature("A", "D", poly(29, -2)),
            feature("B", "D", poly(30, -2)),
        ],
    }

    with pytest.raises(ValueError, match="no feature"):
        resolve_boundary_geometry(json.dumps(data), "Missing", "D")


def test_multipolygon_is_accepted():
    multi = {
        "type": "MultiPolygon",
        "coordinates": [
            poly(29, -2)["coordinates"],
            poly(30, -2)["coordinates"],
        ],
    }

    assert resolve_boundary_geometry(json.dumps(multi), "A", "B") == multi


@pytest.mark.parametrize(
    "ref, message",
    [
        (None, "empty"),
        ("   ", "empty"),
        ("{not json", "valid JSON"),
        (
            '{"type": "Point", "coordinates": [29, -2]}',
            "must be coordinates",
        ),
        ('{"type": "Feature", "geometry": null, "properties": {}}', "geometry"),
    ],
)
def test_bad_references_raise_clear_errors(ref, message):
    with pytest.raises(ValueError, match=message):
        resolve_boundary_geometry(ref, "A", "B")


def test_feature_collection_without_matching_features_is_an_error():
    data = {
        "type": "FeatureCollection",
        "features": [],
    }

    with pytest.raises(ValueError, match="no feature"):
        resolve_boundary_geometry(json.dumps(data), "Missing", "D")
