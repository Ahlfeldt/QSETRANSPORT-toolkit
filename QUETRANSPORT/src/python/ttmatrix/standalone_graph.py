"""Standalone TTMATRIX graph construction and shortest-path routing.

This module mirrors the public Ahlfeldt/TTMATRIX algorithm while accepting
already standardized QUETRANSPORT centroids and configuration values.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from time import perf_counter
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import split

from common.progress import progress_range
from ttmatrix.prepare_travel_times import MatrixInputError


_WORKER_GRAPH: nx.Graph | None = None
_WORKER_TARGETS: tuple[str, ...] = ()


def _initialize_dijkstra_worker(graph: nx.Graph, targets: tuple[str, ...]) -> None:
    """Load one read-only graph in a spawned shortest-path worker."""
    global _WORKER_GRAPH, _WORKER_TARGETS
    _WORKER_GRAPH = graph
    _WORKER_TARGETS = targets


def _dijkstra_worker(origin: int) -> tuple[int, np.ndarray]:
    """Return one origin row using the standalone NetworkX Dijkstra call."""
    if _WORKER_GRAPH is None:
        raise RuntimeError("The TTMATRIX worker graph was not initialized.")
    lengths = nx.single_source_dijkstra_path_length(
        _WORKER_GRAPH, f"point_{origin}", weight="weight"
    )
    row = np.array([lengths.get(target, np.inf) for target in _WORKER_TARGETS])
    return origin, row


def _line_parts(geometry) -> list[LineString]:
    """Return LineString parts without changing their coordinate sequences."""
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return list(geometry.geoms)
    return []


def _snap_network_endpoints(
    network: gpd.GeoDataFrame, tolerance_metres: float
) -> gpd.GeoDataFrame:
    """Replicate standalone TTMATRIX endpoint clustering and centroid snapping."""
    if tolerance_metres <= 0:
        return network.copy()

    parts = [part for geometry in network.geometry for part in _line_parts(geometry)]
    endpoints = [Point(part.coords[position]) for part in parts for position in (0, -1)]
    if not endpoints:
        raise MatrixInputError("The configured network contains no usable lines.")

    endpoint_coordinates = np.array([[point.x, point.y] for point in endpoints])
    endpoint_tree = cKDTree(endpoint_coordinates)
    snapped_coordinates = endpoint_coordinates.copy()
    visited: set[int] = set()

    for endpoint in range(len(endpoint_coordinates)):
        if endpoint in visited:
            continue
        neighbours = endpoint_tree.query_ball_point(
            endpoint_coordinates[endpoint], r=tolerance_metres
        )
        if len(neighbours) > 1:
            visited.update(neighbours)
            cluster_centroid = endpoint_coordinates[neighbours].mean(axis=0)
            snapped_coordinates[neighbours] = cluster_centroid

    coordinate_map = {
        tuple(coordinate): tuple(snapped_coordinates[index])
        for index, coordinate in enumerate(endpoint_coordinates)
    }
    snapped_parts = []
    for part in parts:
        coordinates = [coordinate_map.get(tuple(value), value) for value in part.coords]
        snapped_parts.append(LineString(coordinates))
    return gpd.GeoDataFrame(geometry=snapped_parts, crs=network.crs)


def _split_network_at_stations(
    network: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
    station_buffer_metres: float,
) -> tuple[gpd.GeoDataFrame, int]:
    """Apply the standalone buffered station splitting rule to every line."""
    buffered = stations.geometry.buffer(station_buffer_metres)
    new_lines: list[LineString] = []
    failed_splits = 0

    for line in network.geometry:
        intersecting = buffered[buffered.intersects(line)]
        if intersecting.empty:
            new_lines.append(line)
            continue
        splitter = (
            intersecting.union_all()
            if hasattr(intersecting, "union_all")
            else intersecting.unary_union
        )
        try:
            pieces = split(line, splitter)
            new_lines.extend(piece for piece in pieces.geoms if piece.length > 0)
        except Exception:
            # The standalone script warns and retains the original line.
            failed_splits += 1
            new_lines.append(line)

    return gpd.GeoDataFrame(geometry=new_lines, crs=network.crs), failed_splits


def build_standalone_graph(
    point_coordinates: np.ndarray,
    network: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
    walking_speed_kmh: float,
    network_speed_kmh: float,
    snap_tolerance_metres: float = 1.0,
    station_split_buffer_metres: float = 0.5,
    point_station_neighbours: int = 3,
    point_walking_neighbours: int = 5,
    station_connector_minutes: float = 0.0001,
) -> tuple[nx.Graph, dict[str, Any]]:
    """Build the augmented graph using the public standalone methodology."""
    if len(point_coordinates) < 2:
        raise MatrixInputError("Standalone TTMATRIX routing requires at least two locations.")
    if stations.empty:
        raise MatrixInputError("Standalone TTMATRIX routing requires at least one station.")

    started = perf_counter()
    snapped_network = _snap_network_endpoints(network, snap_tolerance_metres)
    split_network, failed_splits = _split_network_at_stations(
        snapped_network, stations, station_split_buffer_metres
    )

    graph = nx.Graph()
    network_speed_metres_per_minute = network_speed_kmh * 1000.0 / 60.0
    walking_speed_metres_per_minute = walking_speed_kmh * 1000.0 / 60.0

    # Preserve every vertex in each source line and weight transit edges in minutes.
    for line in split_network.geometry:
        coordinates = list(line.coords)
        for first, second in zip(coordinates[:-1], coordinates[1:]):
            distance_metres = LineString([first, second]).length
            graph.add_edge(
                tuple(first), tuple(second),
                weight=distance_metres / network_speed_metres_per_minute,
                edge_type="network",
            )

    network_nodes = [node for node in graph.nodes if isinstance(node, tuple)]
    if not network_nodes:
        raise MatrixInputError("The configured network produced no graph edges.")
    network_coordinates = np.asarray(network_nodes, dtype=float)
    network_tree = cKDTree(network_coordinates)

    # Station-to-network connectors have the same small positive weight as TTMATRIX.
    for position, geometry in enumerate(stations.geometry):
        station_node = f"station_{position}"
        graph.add_node(station_node, geometry=geometry, node_type="station")
        _, nearest_position = network_tree.query([geometry.x, geometry.y], k=1)
        graph.add_edge(
            station_node, network_nodes[int(nearest_position)],
            weight=station_connector_minutes,
            edge_type="station_connector",
        )

    for position, coordinate in enumerate(point_coordinates):
        graph.add_node(
            f"point_{position}", geometry=Point(coordinate), node_type="location"
        )

    # Each location receives walking edges to its nearest configured stations.
    station_coordinates = np.array([[point.x, point.y] for point in stations.geometry])
    station_tree = cKDTree(station_coordinates)
    station_neighbour_count = min(max(int(point_station_neighbours), 1), len(stations))
    for position, coordinate in enumerate(point_coordinates):
        distances, neighbours = station_tree.query(coordinate, k=station_neighbour_count)
        for distance, station in zip(np.atleast_1d(distances), np.atleast_1d(neighbours)):
            graph.add_edge(
                f"point_{position}", f"station_{int(station)}",
                weight=float(distance) / walking_speed_metres_per_minute,
                edge_type="point_station_walk",
            )

    # The undirected graph contains the union of each location's nearest-neighbour links.
    point_tree = cKDTree(point_coordinates)
    walking_neighbour_count = min(
        max(int(point_walking_neighbours), 1), len(point_coordinates) - 1
    )
    for position, coordinate in enumerate(point_coordinates):
        distances, neighbours = point_tree.query(coordinate, k=walking_neighbour_count + 1)
        for neighbour, distance in zip(
            np.atleast_1d(neighbours)[1:], np.atleast_1d(distances)[1:]
        ):
            graph.add_edge(
                f"point_{position}", f"point_{int(neighbour)}",
                weight=float(distance) / walking_speed_metres_per_minute,
                edge_type="point_walk",
            )

    location_subgraph = graph.subgraph(
        [node for node, data in graph.nodes(data=True) if data.get("node_type") == "location"]
    )
    report = {
        "graph_build_seconds": perf_counter() - started,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "network_edges": sum(data.get("edge_type") == "network" for _, _, data in graph.edges(data=True)),
        "station_connector_edges": sum(data.get("edge_type") == "station_connector" for _, _, data in graph.edges(data=True)),
        "point_station_edges": sum(data.get("edge_type") == "point_station_walk" for _, _, data in graph.edges(data=True)),
        "point_walking_edges": sum(data.get("edge_type") == "point_walk" for _, _, data in graph.edges(data=True)),
        "failed_station_splits": failed_splits,
        "walking_only_components": nx.number_connected_components(location_subgraph),
    }
    return graph, report


def build_standalone_walking_graph(
    point_coordinates: np.ndarray,
    walking_speed_kmh: float,
    point_walking_neighbours: int = 5,
) -> tuple[nx.Graph, dict[str, Any]]:
    """Build the standalone nearest-neighbour graph when no network is supplied."""
    if len(point_coordinates) < 2:
        raise MatrixInputError("Standalone TTMATRIX routing requires at least two locations.")
    started = perf_counter()
    graph = nx.Graph()
    walking_speed_metres_per_minute = walking_speed_kmh * 1000.0 / 60.0
    for position, coordinate in enumerate(point_coordinates):
        graph.add_node(
            f"point_{position}", geometry=Point(coordinate), node_type="location"
        )
    point_tree = cKDTree(point_coordinates)
    neighbour_count = min(
        max(int(point_walking_neighbours), 1), len(point_coordinates) - 1
    )
    for position, coordinate in enumerate(point_coordinates):
        distances, neighbours = point_tree.query(coordinate, k=neighbour_count + 1)
        for neighbour, distance in zip(
            np.atleast_1d(neighbours)[1:], np.atleast_1d(distances)[1:]
        ):
            graph.add_edge(
                f"point_{position}", f"point_{int(neighbour)}",
                weight=float(distance) / walking_speed_metres_per_minute,
                edge_type="point_walk",
            )
    return graph, {
        "graph_build_seconds": perf_counter() - started,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "network_edges": 0,
        "station_connector_edges": 0,
        "point_station_edges": 0,
        "point_walking_edges": graph.number_of_edges(),
        "failed_station_splits": 0,
        "walking_only_components": nx.number_connected_components(graph),
    }


def standalone_shortest_path_matrix(
    graph: nx.Graph,
    location_count: int,
    label: str,
    workers: int = 1,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Run the standalone weighted Dijkstra calculation for every location."""
    started = perf_counter()
    targets = tuple(f"point_{position}" for position in range(location_count))
    matrix = np.full((location_count, location_count), np.inf, dtype=float)
    worker_count = max(1, min(int(workers), location_count))

    if worker_count == 1:
        for origin in progress_range(
            range(location_count), total=location_count,
            description=f"TTMATRIX {label}: Dijkstra", unit="origin"
        ):
            lengths = nx.single_source_dijkstra_path_length(
                graph, f"point_{origin}", weight="weight"
            )
            matrix[origin] = [lengths.get(target, np.inf) for target in targets]
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            initializer=_initialize_dijkstra_worker,
            initargs=(graph, targets),
        ) as executor:
            rows = executor.map(_dijkstra_worker, range(location_count), chunksize=8)
            for origin, row in progress_range(
                rows, total=location_count,
                description=f"TTMATRIX {label}: parallel Dijkstra", unit="origin"
            ):
                matrix[origin] = row

    finite = np.isfinite(matrix)
    finite_off_diagonal = finite.copy()
    np.fill_diagonal(finite_off_diagonal, False)
    positive = matrix[finite_off_diagonal]
    report = {
        "shortest_path_seconds": perf_counter() - started,
        "workers": worker_count,
        "unreachable_pairs": int((~finite).sum()),
        "maximum_finite_minutes": float(positive.max()) if positive.size else 0.0,
        "mean_finite_minutes": float(positive.mean()) if positive.size else 0.0,
    }
    return matrix, report
