import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNCTIONS = PROJECT_ROOT / "src" / "python"
if str(FUNCTIONS) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS))

from ttmatrix.generate_travel_times import generate_travel_times


class FundamentalsOnlyTravelTimesTests(unittest.TestCase):
    def test_null_counterfactual_network_reuses_baseline_matrix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standardized = root / "standardized"
            model = standardized / "model"
            geography = standardized / "geography"
            model.mkdir(parents=True)
            geography.mkdir(parents=True)

            ids = ["a", "b", "c"]
            pd.DataFrame({"location_id": ids}).to_csv(
                model / "locations.csv", index=False
            )
            gpd.GeoDataFrame(
                {"location_id": ids},
                geometry=[Point(0, 0), Point(1000, 0), Point(0, 1000)],
                crs="EPSG:3857",
            ).to_file(
                geography / "centroids.gpkg",
                layer="centroids",
                driver="GPKG",
            )

            config = {
                "paths": {
                    "standardized_input": str(standardized),
                    "output": str(root / "outputs"),
                    "baseline_network": None,
                    "baseline_stations": None,
                    "counterfactual_network": None,
                    "counterfactual_stations": None,
                },
                "ttmatrix": {
                    "analysis_crs": "EPSG:3857",
                    "off_network_speed_kmh": 20,
                    "network_speed_kmh": 33,
                    "intrazonal_rule": "configured_constant",
                    "intrazonal_minutes": 1.0,
                },
            }

            report = generate_travel_times(config)
            matrix_dir = standardized / "travel_times"
            baseline = pd.read_csv(
                matrix_dir / "travel_times_baseline.csv", index_col=0
            ).to_numpy()
            counterfactual = pd.read_csv(
                matrix_dir / "travel_times_counterfactual.csv", index_col=0
            ).to_numpy()

            np.testing.assert_array_equal(counterfactual, baseline)
            self.assertEqual(report["improved_pairs"], 0)
            self.assertEqual(report["slower_pairs"], 0)
            self.assertEqual(report["unchanged_pairs"], len(ids) ** 2)
            self.assertIn("no transport intervention", report["counterfactual_definition"])


if __name__ == "__main__":
    unittest.main()

