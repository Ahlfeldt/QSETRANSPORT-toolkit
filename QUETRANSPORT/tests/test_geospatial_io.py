"""Regression tests for network-safe GeoPackage publication."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

SOURCE = Path(__file__).resolve().parents[1] / "src" / "python"
sys.path.insert(0, str(SOURCE))

from common.geospatial_io import write_geopackage


def test_write_geopackage_replaces_target_with_readable_file(tmp_path):
    target = tmp_path / "locations.gpkg"
    target.write_bytes(b"previous file remains until publication")
    frame = gpd.GeoDataFrame(
        {"location_id": [1, 2]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )

    result = write_geopackage(frame, target, layer="locations")

    assert result == target
    restored = gpd.read_file(target, layer="locations")
    assert restored["location_id"].tolist() == [1, 2]
    assert not list(tmp_path.glob("*.copying.gpkg"))
