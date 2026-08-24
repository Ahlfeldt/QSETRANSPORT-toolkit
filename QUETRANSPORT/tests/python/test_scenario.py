import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, box

from common.scenario import ScenarioInputError, prepare_primitive_shocks
from reporting.make_shock_maps import make_shock_maps


class PolygonPrimitiveShockTests(unittest.TestCase):
    def make_project(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        standardized = root / "standardized"
        (standardized / "model").mkdir(parents=True)
        (standardized / "geography").mkdir(parents=True)
        (root / "outputs" / "diagnostics").mkdir(parents=True)
        pd.DataFrame({"location_id": ["a", "b"]}).to_csv(
            standardized / "model" / "locations.csv", index=False
        )
        target = gpd.GeoDataFrame(
            {"location_id": ["a", "b"]},
            geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
            crs="EPSG:3857",
        )
        target.to_file(standardized / "geography" / "locations.gpkg", layer="locations", driver="GPKG")
        config = {
            "paths": {"standardized_input": str(standardized), "output": str(root / "outputs")},
            "reporting": {"make_maps": True, "map_format": "png"},
            "ttmatrix": {"source": "user_provided"},
            "scenario": {
                "shocks_shapefile": None,
                "analysis_crs": "EPSG:3857",
                "productivity_hat_variable": "prod_hat",
                "amenity_hat_variable": None,
                "structural_density_hat_variable": None,
            },
        }
        return temporary, root, config

    def write_policy(self, root, geometries, values):
        path = root / "policy.gpkg"
        gpd.GeoDataFrame({"prod_hat": values}, geometry=geometries, crs="EPSG:3857").to_file(
            path, layer="policy", driver="GPKG"
        )
        return path

    def test_null_geography_means_no_changes(self):
        temporary, root, config = self.make_project()
        self.addCleanup(temporary.cleanup)
        report = prepare_primitive_shocks(config)
        self.assertFalse(report["active"])
        self.assertFalse((root / "standardized" / "shocks" / "shocks.csv").exists())

    def test_partial_overlap_assigns_uncovered_area_hat_one(self):
        temporary, root, config = self.make_project()
        self.addCleanup(temporary.cleanup)
        # A 20% shock covers half of cell a: its interpolated hat is 1.10.
        config["scenario"]["shocks_shapefile"] = str(
            self.write_policy(root, [box(0, 0, 5, 10)], [1.2])
        )
        report = prepare_primitive_shocks(config)
        shocks = pd.read_csv(report["standardized_file"])
        self.assertAlmostEqual(shocks.loc[0, "productivity_hat"], 1.1)
        self.assertAlmostEqual(shocks.loc[1, "productivity_hat"], 1.0)
        self.assertTrue((shocks["amenity_hat"] == 1.0).all())

        # Exercise the map's transport-innovation overlay. With no baseline
        # network, the entire counterfactual line is the innovation.
        network_path = root / "innovation.gpkg"
        gpd.GeoDataFrame(
            {"name": ["policy line"]},
            geometry=[LineString([(0, 5), (20, 5)])],
            crs="EPSG:3857",
        ).to_file(network_path, layer="network", driver="GPKG")
        config["ttmatrix"]["source"] = "ttmatrix"
        config["paths"]["counterfactual_network"] = str(network_path)
        config["paths"]["baseline_network"] = None
        map_paths = make_shock_maps(config, report)
        self.assertEqual(len(map_paths), 6)
        self.assertEqual({path.suffix for path in map_paths}, {".pdf", ".png"})
        for map_path in map_paths:
            self.assertTrue(map_path.is_file())
            self.assertGreater(map_path.stat().st_size, 0)

    def test_overlapping_policy_polygons_stop(self):
        temporary, root, config = self.make_project()
        self.addCleanup(temporary.cleanup)
        config["scenario"]["shocks_shapefile"] = str(
            self.write_policy(root, [box(0, 0, 8, 10), box(2, 0, 10, 10)], [1.1, 1.2])
        )
        with self.assertRaisesRegex(ScenarioInputError, "overlap"):
            prepare_primitive_shocks(config)

    def test_missing_configured_field_stops(self):
        temporary, root, config = self.make_project()
        self.addCleanup(temporary.cleanup)
        config["scenario"]["shocks_shapefile"] = str(
            self.write_policy(root, [box(0, 0, 10, 10)], [1.1])
        )
        config["scenario"]["productivity_hat_variable"] = "wrong_name"
        with self.assertRaisesRegex(ScenarioInputError, "was not found"):
            prepare_primitive_shocks(config)


if __name__ == "__main__":
    unittest.main()