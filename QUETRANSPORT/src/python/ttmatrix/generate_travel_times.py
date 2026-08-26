"""Generate baseline and counterfactual matrices from optional transport networks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import nearest_points, split, unary_union

from common.identifiers import canonical_series
from common.progress import progress_range
from ttmatrix.prepare_travel_times import MatrixInputError


def _projected_crs(points: gpd.GeoDataFrame, configured: str | None):
    if configured:
        crs = points.to_crs(configured).crs
        if crs.is_geographic:
            raise MatrixInputError("ttmatrix.analysis_crs must be projected in metres.")
        return crs
    crs = points.estimate_utm_crs()
    if crs is None:
        raise MatrixInputError("Could not infer routing CRS; set ttmatrix.analysis_crs.")
    return crs


def _segments(geometry):
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return list(geometry.geoms)
    return []


def _network_station_distances(
    network: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
    label: str,
) -> tuple[np.ndarray, list[Point]]:
    """Node one network at intersections and snapped stations, then run Dijkstra."""
    merged = unary_union(list(network.geometry))
    lines = _segments(merged)
    if not lines:
        raise MatrixInputError(f"{label} network contains no usable lines.")

    snapped = []
    for station in progress_range(stations.geometry, total=len(stations), description=f"TTMATRIX {label}: snap stations", unit="station"):
        nearest_line = min(lines, key=lambda line: line.distance(station))
        snapped.append(nearest_line.interpolate(nearest_line.project(station)))

    split_lines = []
    for line in progress_range(lines, total=len(lines), description=f"TTMATRIX {label}: node network", unit="line"):
        points_on_line = [point for point in snapped if line.distance(point) < 1e-6 and
                          point.distance(Point(line.coords[0])) > 1e-6 and
                          point.distance(Point(line.coords[-1])) > 1e-6]
        pieces = [line]
        for point in points_on_line:
            updated = []
            for piece in pieces:
                if piece.distance(point) < 1e-6 and point.distance(Point(piece.coords[0])) > 1e-6 and point.distance(Point(piece.coords[-1])) > 1e-6:
                    try:
                        updated.extend(list(split(piece, point).geoms))
                    except Exception:
                        updated.append(piece)
                else:
                    updated.append(piece)
            pieces = updated
        split_lines.extend(pieces)

    graph = nx.Graph()
    precision = 6
    def key(coord):
        return (round(coord[0], precision), round(coord[1], precision))
    for line in split_lines:
        coords = list(line.coords)
        for first, second in zip(coords[:-1], coords[1:]):
            a, b = key(first), key(second)
            length = Point(first).distance(Point(second))
            if length > 0:
                if graph.has_edge(a, b):
                    graph[a][b]["length"] = min(graph[a][b]["length"], length)
                else:
                    graph.add_edge(a, b, length=length)

    station_nodes = []
    for point in snapped:
        candidate = key(point.coords[0])
        if candidate not in graph:
            candidate = min(graph.nodes, key=lambda node: Point(node).distance(point))
        station_nodes.append(candidate)
    distances = np.full((len(station_nodes), len(station_nodes)), np.inf)
    for i, node in progress_range(enumerate(station_nodes), total=len(station_nodes), description=f"TTMATRIX {label}: shortest paths", unit="origin"):
        lengths = nx.single_source_dijkstra_path_length(graph, node, weight="length")
        for j, target in enumerate(station_nodes):
            if target in lengths:
                distances[i, j] = lengths[target]
    if not np.isfinite(distances).all():
        raise MatrixInputError(f"Some configured stations are disconnected on the {label} network.")
    return distances, snapped


def _travel_matrix_with_network(
    direct_minutes: np.ndarray,
    centroid_coords: np.ndarray,
    network_path: Path,
    station_path: Path,
    routing_crs,
    offnetwork_speed: float,
    network_speed: float,
    label: str,
) -> tuple[np.ndarray, int]:
    """Combine direct travel with access, network travel, and egress."""
    if not network_path.is_file() or not station_path.is_file():
        raise MatrixInputError(
            f"{label.capitalize()} network and station files do not exist: "
            f"{network_path}; {station_path}"
        )
    network = gpd.read_file(network_path).to_crs(routing_crs)
    stations = gpd.read_file(station_path).to_crs(routing_crs)
    if stations.empty:
        raise MatrixInputError(f"{label.capitalize()} station file contains no stations.")
    if not stations.geom_type.eq("Point").all():
        stations["geometry"] = stations.geometry.centroid

    station_distance, snapped = _network_station_distances(network, stations, label)
    station_coords = np.array([[point.x, point.y] for point in snapped])
    access = cdist(centroid_coords, station_coords) / (offnetwork_speed * 1000.0 / 60.0)
    network_minutes = station_distance / (network_speed * 1000.0 / 60.0)

    result = direct_minutes.copy()
    for origin_station in progress_range(range(len(stations)), total=len(stations), description=f"TTMATRIX {label}: OD alternatives", unit="station"):
        for destination_station in range(len(stations)):
            candidate = (
                access[:, origin_station, None]
                + network_minutes[origin_station, destination_station]
                + access[:, destination_station][None, :]
            )
            result = np.minimum(result, candidate)
    return result, int(len(stations))


def generate_travel_times(config: dict[str, Any]) -> dict[str, Any]:
    input_root = Path(config["paths"]["standardized_input"])
    locations = pd.read_csv(input_root / "model" / "locations.csv", dtype={"location_id": "string"})
    ids = canonical_series(locations["location_id"]).tolist()
    centroid_path = input_root / "geography" / "centroids.gpkg"
    centroids = gpd.read_file(centroid_path, layer="centroids")
    centroids["location_id"] = canonical_series(centroids["location_id"])
    centroids = centroids.set_index("location_id").reindex(ids)
    if centroids.geometry.isna().any():
        raise MatrixInputError("Centroid geography does not contain every standardized location ID.")

    tt_cfg = config["ttmatrix"]
    routing_crs = _projected_crs(centroids, tt_cfg.get("analysis_crs"))
    centroids = centroids.to_crs(routing_crs)
    coords = np.column_stack((centroids.geometry.x, centroids.geometry.y))
    offnetwork_speed = float(tt_cfg["off_network_speed_kmh"])
    network_speed = float(tt_cfg["network_speed_kmh"])
    if offnetwork_speed <= 0 or network_speed <= 0:
        raise MatrixInputError("Both routing speeds must be positive.")
    direct_distance = cdist(coords, coords)
    direct_minutes = direct_distance / (offnetwork_speed * 1000.0 / 60.0)

    # Null baseline paths mean direct off-network baseline travel. If both files
    # are supplied, route through the initial network using the same algorithm.
    baseline_network = config["paths"].get("baseline_network")
    baseline_stations = config["paths"].get("baseline_stations")
    if baseline_network and baseline_stations:
        baseline, baseline_station_count = _travel_matrix_with_network(
            direct_minutes, coords, Path(baseline_network), Path(baseline_stations),
            routing_crs, offnetwork_speed, network_speed, "baseline"
        )
        baseline_definition = "minimum of direct travel and baseline access-network-egress travel"
    else:
        baseline = direct_minutes.copy()
        baseline_station_count = 0
        baseline_definition = "direct centroid-to-centroid travel without a baseline network"

    # Null counterfactual paths mean no transport intervention. Reuse the
    # complete baseline matrix, whether the baseline is direct travel or was
    # constructed from an initial network. This permits fundamentals-only
    # counterfactuals without introducing a spurious network change.
    counterfactual_network = config["paths"].get("counterfactual_network")
    counterfactual_stations = config["paths"].get("counterfactual_stations")
    if counterfactual_network and counterfactual_stations:
        counterfactual, counterfactual_station_count = _travel_matrix_with_network(
            direct_minutes, coords,
            Path(counterfactual_network), Path(counterfactual_stations),
            routing_crs, offnetwork_speed, network_speed, "counterfactual"
        )
        counterfactual_definition = (
            "minimum of direct travel and counterfactual access-network-egress travel"
        )
    else:
        counterfactual = baseline.copy()
        counterfactual_station_count = baseline_station_count
        counterfactual_definition = "identical to baseline travel (no transport intervention)"

    rule = tt_cfg.get("intrazonal_rule", "keep")
    if rule == "configured_constant":
        intrazonal = float(tt_cfg.get("intrazonal_minutes", 0.0))
        np.fill_diagonal(baseline, intrazonal)
        np.fill_diagonal(counterfactual, intrazonal)
    elif rule != "keep":
        raise MatrixInputError("ttmatrix.intrazonal_rule must be keep or configured_constant.")

    matrix_dir = input_root / "travel_times"
    diagnostics_dir = Path(config["paths"]["output"]) / "diagnostics"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    columns = [f"location_id_{value}" for value in ids]
    baseline_df = pd.DataFrame(baseline, index=ids, columns=columns)
    counterfactual_df = pd.DataFrame(counterfactual, index=ids, columns=columns)
    baseline_df.index.name = "location_id"
    counterfactual_df.index.name = "location_id"
    baseline_df.to_csv(matrix_dir / "travel_times_baseline.csv")
    counterfactual_df.to_csv(matrix_dir / "travel_times_counterfactual.csv")

    difference = counterfactual - baseline
    report = {
        "mode": "generate_from_network",
        "number_of_locations": len(ids),
        "baseline_number_of_stations": baseline_station_count,
        "counterfactual_number_of_stations": counterfactual_station_count,
        "baseline_definition": baseline_definition,
        "counterfactual_definition": counterfactual_definition,
        "off_network_speed_kmh": offnetwork_speed,
        "network_speed_kmh": network_speed,
        "routing_crs": str(routing_crs),
        "baseline_mean_minutes": float(baseline.mean()),
        "counterfactual_mean_minutes": float(counterfactual.mean()),
        "matrix_correlation": float(np.corrcoef(baseline.ravel(), counterfactual.ravel())[0, 1]),
        "improved_pairs": int((difference < -1e-10).sum()),
        "unchanged_pairs": int((np.abs(difference) <= 1e-10).sum()),
        "slower_pairs": int((difference > 1e-10).sum()),
    }
    (diagnostics_dir / "travel_time_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
