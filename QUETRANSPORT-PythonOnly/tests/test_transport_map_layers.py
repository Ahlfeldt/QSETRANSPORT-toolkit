import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from reporting.make_maps import _transport_layers


class TransportMapLayerTests(unittest.TestCase):
    def test_existing_added_and_removed_links_are_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_path = root / "baseline.gpkg"
            counterfactual_path = root / "counterfactual.gpkg"
            gpd.GeoDataFrame(
                geometry=[
                    LineString([(0, 5), (10, 5)]),
                    LineString([(0, 8), (5, 8)]),
                ],
                crs="EPSG:3857",
            ).to_file(baseline_path, driver="GPKG")
            gpd.GeoDataFrame(
                geometry=[LineString([(0, 5), (20, 5)])],
                crs="EPSG:3857",
            ).to_file(counterfactual_path, driver="GPKG")
            config = {
                "ttmatrix": {"source": "ttmatrix"},
                "paths": {
                    "baseline_network": str(baseline_path),
                    "counterfactual_network": str(counterfactual_path),
                },
            }

            existing, added, removed = _transport_layers(config, "EPSG:3857")

            self.assertIsNotNone(existing)
            self.assertIsNotNone(added)
            self.assertIsNotNone(removed)
            self.assertEqual(len(existing), 2)
            self.assertGreater(float(added.geometry.length.sum()), 8.0)
            self.assertGreater(float(removed.geometry.length.sum()), 3.0)


if __name__ == "__main__":
    unittest.main()
