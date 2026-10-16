import json

import pytest

from services.boundary import resolve_boundary_geometry
from services.errors import InvalidGeometryError


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


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


def test_inline_geojson_string():
    geometry = poly(29, -2)
    assert resolve_boundary_geometry(json.dumps(geometry), "A", "B") == geometry


def test_feature_collection_matches_by_sector_name(tmp_path):
    a, b = poly(29, -2), poly(30, -2)
    path = write(
        tmp_path,
        "sectors.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                feature("Gisenyi", "Rubavu", a),
                feature("Kanama", "Rubavu", b),
            ],
        },
    )
    assert resolve_boundary_geometry(str(path), "Kanama", "Rubavu") == b
    assert (
        resolve_boundary_geometry(str(path), "  gisenyi ", "rubavu") == a
    )  # case/space tolerant


def test_relative_path_uses_base_dir(tmp_path):
    geometry = poly(29, -2)
    write(
        tmp_path,
        "one.geojson",
        {"type": "Feature", "properties": {}, "geometry": geometry},
    )
    assert (
        resolve_boundary_geometry("one.geojson", "X", "Y", base_dir=str(tmp_path))
        == geometry
    )


def test_same_sector_name_in_two_districts_needs_the_district(tmp_path):
    a, b = poly(29, -2), poly(30, -2)
    path = write(
        tmp_path,
        "s.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                feature("Nyamyumba", "Rubavu", a),
                feature("Nyamyumba", "Karongi", b),
            ],
        },
    )
    assert resolve_boundary_geometry(str(path), "Nyamyumba", "Karongi") == b
    with pytest.raises(InvalidGeometryError, match="none is in district"):
        resolve_boundary_geometry(str(path), "Nyamyumba", "Unknown District")


def test_single_feature_file_is_used_without_name_match(tmp_path):
    geometry = poly(29, -2)
    path = write(
        tmp_path,
        "one.geojson",
        {
            "type": "FeatureCollection",
            "features": [feature("Whatever", "Elsewhere", geometry)],
        },
    )
    assert resolve_boundary_geometry(str(path), "Other", "Other") == geometry


def test_no_matching_feature_is_an_error(tmp_path):
    path = write(
        tmp_path,
        "s.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                feature("A", "D", poly(29, -2)),
                feature("B", "D", poly(30, -2)),
            ],
        },
    )
    with pytest.raises(InvalidGeometryError, match="no feature"):
        resolve_boundary_geometry(str(path), "Missing", "D")


def test_multipolygon_is_accepted(tmp_path):
    multi = {
        "type": "MultiPolygon",
        "coordinates": [poly(29, -2)["coordinates"], poly(30, -2)["coordinates"]],
    }
    assert resolve_boundary_geometry(json.dumps(multi), "A", "B") == multi


@pytest.mark.parametrize(
    "ref, message",
    [
        (None, "empty"),
        ("   ", "empty"),
        ("{not json", "invalid inline"),
        ('{"type": "Point", "coordinates": [29, -2]}', "unsupported geometry"),
        ("https://example.org/sectors.geojson", "remote"),
        ("data/sectors.shp", "only GeoJSON"),
        ("does/not/exist.geojson", "not found"),
    ],
)
def test_bad_references_raise_clear_errors(ref, message):
    with pytest.raises(InvalidGeometryError, match=message):
        resolve_boundary_geometry(ref, "A", "B")


def test_file_that_is_not_json_is_an_error(tmp_path):
    path = tmp_path / "bad.geojson"
    path.write_text("this is not json")
    with pytest.raises(InvalidGeometryError, match="not valid GeoJSON"):
        resolve_boundary_geometry(str(path), "A", "B")
