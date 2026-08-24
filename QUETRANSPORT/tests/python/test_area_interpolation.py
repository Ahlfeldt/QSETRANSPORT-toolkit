
"""Regression tests for polygon intersection-area attribution."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "python"))

from grid.generate_grid_inputs import _area_interpolate, generate_grid_inputs


class AreaInterpolationTest(unittest.TestCase):
    def test_extensive_mass_and_intensive_weighted_mean(self):
        source = gpd.GeoDataFrame(
            {"population": [100.0, 200.0], "rent": [10.0, 30.0]},
            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
            crs=3857,
        )
        target = gpd.GeoDataFrame(
            {"grid_sequence": [1, 2]},
            geometry=[box(0, 0, 1.5, 1), box(1.5, 0, 2, 1)],
            crs=3857,
        )

        result, diagnostics = _area_interpolate(
            source,
            target,
            extensive_columns=["population"],
            intensive_columns=["rent"],
            chunk_size=1,
        )

        self.assertAlmostEqual(result.loc[0, "population"], 200.0)
        self.assertAlmostEqual(result.loc[1, "population"], 100.0)
        self.assertAlmostEqual(result["population"].sum(), 300.0)
        self.assertAlmostEqual(result.loc[0, "rent"], (10.0 * 1.0 + 30.0 * 0.5) / 1.5)
        self.assertAlmostEqual(result.loc[1, "rent"], 30.0)
        self.assertAlmostEqual(diagnostics["population_allocation_ratio"], 1.0)

    def test_original_mode_preserves_source_polygons_and_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_folder = root / "raw_grid"
            source_folder.mkdir()
            source = gpd.GeoDataFrame(
                {
                    "zone_id": ["west", "east"],
                    "population": [100.0, 200.0],
                    "employment": [120.0, 180.0],
                },
                geometry=[box(0, 0, 1_000, 1_000), box(1_000, 0, 2_000, 1_000)],
                crs="EPSG:3857",
            )
            source.to_file(source_folder / "zones.gpkg", layer="zones", driver="GPKG")
            config = {
                "paths": {
                    "source_grid_folder": str(source_folder),
                    "standardized_input": str(root / "standardized"),
                    "output": str(root / "outputs"),
                },
                "grid": {
                    "cell_geometry": "original",
                    "cell_size_km": 999.0,  # Deliberately ignored in original mode.
                    "original_id_variable": "zone_id",
                    "analysis_crs": "EPSG:3857",
                    "output_crs": "EPSG:3857",
                    "population_source_variable": "population",
                    "employment_source_variable": "employment",
                    "developed_source_variable": None,
                    "total_population": 300.0,
                    "rent_source_variable": None,
                    "synthetic_rent_population_elasticity": 0.0,
                    "synthetic_rent_random_spread": 0.0,
                    "random_seed": 1,
                },
            }

            report = generate_grid_inputs(config)
            locations = pd.read_csv(
                root / "standardized" / "model" / "locations.csv",
                dtype={"location_id": "string"},
            )
            output = gpd.read_file(
                root / "standardized" / "geography" / "locations.gpkg",
                layer="locations",
            ).set_index("location_id").loc[["west", "east"]]
            expected = source.set_index("zone_id").loc[["west", "east"]]

            self.assertEqual(report["cell_geometry"], "original")
            self.assertIsNone(report["cell_size_km"])
            self.assertEqual(locations["location_id"].tolist(), ["west", "east"])
            self.assertAlmostEqual(locations["population"].sum(), 300.0)
            for identifier in ("west", "east"):
                difference = output.loc[identifier].geometry.symmetric_difference(
                    expected.loc[identifier].geometry
                )
                self.assertAlmostEqual(difference.area, 0.0)

if __name__ == "__main__":
    unittest.main()
