import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from shapely.geometry import LineString, Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = PROJECT_ROOT / "src" / "python"
if str(FUNCTIONS) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS))

from ttmatrix.generate_travel_times import _network_station_distances, _travel_matrix_with_network, generate_travel_times


class FundamentalsOnlyTravelTimesTests(unittest.TestCase):
    def test_candidate_router_matches_exhaustive_router_when_using_all_stations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            network_path, station_path = root / "lines.gpkg", root / "stations.gpkg"
            network = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (3000, 0)])], crs="EPSG:3857")
            stations = gpd.GeoDataFrame(geometry=[Point(0, 0), Point(1500, 0), Point(3000, 0)], crs="EPSG:3857")
            network.to_file(network_path, driver="GPKG")
            stations.to_file(station_path, driver="GPKG")
            coordinates = np.array([[0, 500], [1000, 500], [2000, 500], [3000, 500]])
            direct = cdist(coordinates, coordinates) / (5 * 1000 / 60)
            routed, _ = _travel_matrix_with_network(direct, coordinates, network_path, station_path, "EPSG:3857", 5, 60, "test", station_candidates=None, workers=2)
            station_distance, snapped = _network_station_distances(network, stations, "reference")
            station_coordinates = np.array([[point.x, point.y] for point in snapped])
            access = cdist(coordinates, station_coordinates) / (5 * 1000 / 60)
            network_minutes = station_distance / (60 * 1000 / 60)
            exhaustive = direct.copy()
            for origin_station in range(len(stations)):
                for destination_station in range(len(stations)):
                    exhaustive = np.minimum(exhaustive, access[:, origin_station, None] + network_minutes[origin_station, destination_station] + access[:, destination_station][None, :])
            np.testing.assert_allclose(routed, exhaustive, atol=1e-12)

    def test_nearest_station_router_is_symmetric_and_keeps_direct_walking(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            network_path, station_path = root / "lines.gpkg", root / "stations.gpkg"
            gpd.GeoDataFrame(geometry=[LineString([(0, 0), (3000, 0)])], crs="EPSG:3857").to_file(network_path, driver="GPKG")
            gpd.GeoDataFrame(geometry=[Point(0, 0), Point(1500, 0), Point(3000, 0)], crs="EPSG:3857").to_file(station_path, driver="GPKG")
            coordinates = np.array([[0, 500], [1000, 500], [2000, 500], [3000, 500]])
            direct = cdist(coordinates, coordinates) / (5 * 1000 / 60)
            routed, _ = _travel_matrix_with_network(direct, coordinates, network_path, station_path, "EPSG:3857", 5, 60, "test", station_candidates=1, workers=1)
            np.testing.assert_allclose(routed, routed.T, atol=1e-12)
            self.assertTrue(np.all(routed <= direct + 1e-12))

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

