import pytest

from services.geometry import compute_centroid, validate_geometry

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[29, -2], [30, -2], [30, -1], [29, -1], [29, -2]]],
}


def test_polygon_and_multipolygon_are_valid():
    assert validate_geometry(SQUARE) is SQUARE
    multi = {
        "type": "MultiPolygon",
        "coordinates": [SQUARE["coordinates"], SQUARE["coordinates"]],
    }
    assert validate_geometry(multi) is multi


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"type": "Point", "coordinates": [29, -2]},
        {"type": "Polygon", "coordinates": []},
        {"type": "Polygon", "coordinates": [[[29, -2], [30, -2], [29, -2]]]},
        {"type": "Polygon", "coordinates": [[[29, -2], [30, -2], [30, -1], [29, -1]]]},
        {
            "type": "Polygon",
            "coordinates": [[[299, -2], [30, -2], [30, -1], [299, -2]]],
        },
    ],
)
def test_invalid_geometry_is_rejected(bad):
    with pytest.raises(ValueError):
        validate_geometry(bad)


def test_centroid_of_square_is_its_middle_as_lat_lon():
    lat, lon = compute_centroid(SQUARE)
    assert lat == pytest.approx(-1.5)
    assert lon == pytest.approx(29.5)


def test_centroid_of_multipolygon_is_area_weighted():
    small = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
    big = [[[10, 0], [13, 0], [13, 3], [10, 3], [10, 0]]]
    lat, lon = compute_centroid({"type": "MultiPolygon", "coordinates": [small, big]})
    assert lon == pytest.approx((0.5 * 1 + 11.5 * 9) / 10)
    assert lat == pytest.approx((0.5 * 1 + 1.5 * 9) / 10)
