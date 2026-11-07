import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNCTIONS = PROJECT_ROOT / "src" / "python"
if str(FUNCTIONS) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS))

from ttmatrix.generate_travel_times import generate_travel_times
from ttmatrix.standalone_graph import (
    build_standalone_graph,
    standalone_shortest_path_matrix,
)


def unchanged_standalone_reference(
    point_coordinates: np.ndarray,
    station_coordinates: np.ndarray,
    network_line: LineString,
    walking_speed_kmh: float,
    network_speed_kmh: float,
) -> np.ndarray:
    """Minimal transcription of public Ahlfeldt/TTMATRIX graph construction."""
    graph = nx.Graph()
    coordinates = list(network_line.coords)
    for first, second in zip(coordinates[:-1], coordinates[1:]):
        distance = LineString([first, second]).length
        graph.add_edge(first, second, weight=(distance / 1000) / network_speed_kmh * 60)

    network_nodes = [node for node in graph.nodes if isinstance(node, tuple)]
    network_tree = cKDTree(np.asarray(network_nodes))
    for station, coordinate in enumerate(station_coordinates):
        graph.add_node(f"station_{station}", geometry=Point(coordinate))
        _, nearest = network_tree.query(coordinate, k=1)
        graph.add_edge(f"station_{station}", network_nodes[int(nearest)], weight=0.0001)

    station_tree = cKDTree(station_coordinates)
    for location, coordinate in enumerate(point_coordinates):
        graph.add_node(f"point_{location}", geometry=Point(coordinate))
        distances, stations = station_tree.query(coordinate, k=3)
        for distance, station in zip(distances, stations):
            graph.add_edge(
                f"point_{location}", f"station_{station}",
                weight=(distance / 1000) / walking_speed_kmh * 60,
            )

    point_tree = cKDTree(point_coordinates)
    for location, coordinate in enumerate(point_coordinates):
        distances, neighbours = point_tree.query(coordinate, k=6)
        for neighbour, distance in zip(neighbours[1:], distances[1:]):
            graph.add_edge(
                f"point_{location}", f"point_{neighbour}",
                weight=(distance / 1000) / walking_speed_kmh * 60,
            )

    matrix = np.empty((len(point_coordinates), len(point_coordinates)))
    for origin in range(len(point_coordinates)):
        lengths = nx.single_source_dijkstra_path_length(
            graph, f"point_{origin}", weight="weight"
        )
        matrix[origin] = [lengths[f"point_{destination}"] for destination in range(len(point_coordinates))]
    return matrix


class StandaloneTTMatrixTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([
            [0.0, 500.0], [600.0, 450.0], [1200.0, 550.0],
            [1800.0, 500.0], [2400.0, 450.0], [3000.0, 550.0],
        ])
        self.station_coordinates = np.array([
            [0.0, 0.0], [1500.0, 0.0], [3000.0, 0.0]
        ])
        self.network_line = LineString([(0, 0), (1500, 0), (3000, 0)])

    def test_graph_and_dijkstra_match_unchanged_standalone_transcription(self):
        network = gpd.GeoDataFrame(geometry=[self.network_line], crs="EPSG:3857")
        stations = gpd.GeoDataFrame(
            geometry=[Point(value) for value in self.station_coordinates], crs="EPSG:3857"
        )
        graph, _ = build_standalone_graph(
            self.points, network, stations, 4.0, 35.0,
            snap_tolerance_metres=1.0,
            station_split_buffer_metres=0.5,
            point_station_neighbours=3,
            point_walking_neighbours=5,
            station_connector_minutes=0.0001,
        )
        actual, report = standalone_shortest_path_matrix(
            graph, len(self.points), "test", workers=1
        )
        expected = unchanged_standalone_reference(
            self.points, self.station_coordinates, self.network_line, 4.0, 35.0
        )
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)
        self.assertEqual(report["unreachable_pairs"], 0)

    def test_end_to_end_preserves_ids_minutes_diagonal_and_finite_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standardized = root / "standardized"
            (standardized / "model").mkdir(parents=True)
            (standardized / "geography").mkdir(parents=True)
            identifiers = ["z6", "z1", "z4", "z2", "z5", "z3"]
            pd.DataFrame({"location_id": identifiers}).to_csv(
                standardized / "model" / "locations.csv", index=False
            )
            gpd.GeoDataFrame(
                {"location_id": identifiers},
                geometry=[Point(value) for value in self.points], crs="EPSG:3857",
            ).to_file(standardized / "geography" / "centroids.gpkg", layer="centroids", driver="GPKG")
            network_path, station_path = root / "lines.gpkg", root / "stations.gpkg"
            gpd.GeoDataFrame(geometry=[self.network_line], crs="EPSG:3857").to_file(network_path, driver="GPKG")
            gpd.GeoDataFrame(
                geometry=[Point(value) for value in self.station_coordinates], crs="EPSG:3857"
            ).to_file(station_path, driver="GPKG")
            config = {
                "paths": {
                    "standardized_input": str(standardized), "output": str(root / "outputs"),
                    "baseline_network": str(network_path), "baseline_stations": str(station_path),
                    "counterfactual_network": str(network_path), "counterfactual_stations": str(station_path),
                },
                "ttmatrix": {
                    "routing_method": "standalone_ttmatrix", "analysis_crs": "EPSG:3857",
                    "off_network_speed_kmh": 4, "network_speed_kmh": 35,
                    "point_station_neighbors": 3, "point_walking_neighbors": 5,
                    "snap_tolerance_m": 1.0, "station_split_buffer_m": 0.5,
                    "station_connector_minutes": 0.0001, "workers": 1,
                    "unreachable_rule": "stop", "intrazonal_rule": "configured_constant",
                    "intrazonal_minutes": 1.0,
                },
            }
            generate_travel_times(config)
            output = pd.read_csv(
                standardized / "travel_times" / "travel_times_baseline.csv", index_col=0
            )
            self.assertEqual(output.index.astype(str).tolist(), identifiers)
            self.assertEqual(output.columns.tolist(), [f"location_id_{value}" for value in identifiers])
            self.assertTrue(np.isfinite(output.to_numpy()).all())
            np.testing.assert_array_equal(np.diag(output), np.ones(len(identifiers)))


if __name__ == "__main__":
    unittest.main()
