"""Generate baseline and counterfactual matrices from optional transport networks."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
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
from ttmatrix.standalone_graph import (
    build_standalone_graph,
    build_standalone_walking_graph,
    standalone_shortest_path_matrix,
)


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


def _travel_matrix_with_network_legacy(
    direct_minutes: np.ndarray,
    centroid_coords: np.ndarray,
    network_path: Path,
    station_path: Path,
    routing_crs,
    offnetwork_speed: float,
    network_speed: float,
    label: str,
    station_candidates: int | None = 3,
    workers: int = 1,
) -> tuple[np.ndarray, int]:
    """Combine walking and network travel using TTMATRIX candidate access."""
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

    # The legacy method retains direct walking and minimizes over configured
    # station access, network travel, and egress alternatives.
    station_count = len(stations)
    candidate_count = station_count if station_candidates is None else min(
        max(int(station_candidates), 1), station_count
    )
    nearest = np.argpartition(access, candidate_count - 1, axis=1)[:, :candidate_count]
    nearest_access = np.take_along_axis(access, nearest, axis=1)
    order = np.argsort(nearest_access, axis=1, kind="stable")
    nearest = np.take_along_axis(nearest, order, axis=1)
    nearest_access = np.take_along_axis(nearest_access, order, axis=1)

    result = np.empty_like(direct_minutes)
    location_count = len(centroid_coords)
    worker_count = max(1, min(int(workers), location_count))
    block_size = max(1, (location_count + worker_count * 8 - 1) // (worker_count * 8))
    blocks = [(start, min(start + block_size, location_count))
              for start in range(0, location_count, block_size)]

    def route_block(bounds: tuple[int, int]) -> tuple[int, np.ndarray]:
        """Route one origin block; NumPy kernels release the GIL to workers."""
        start, stop = bounds
        routed = np.empty((stop - start, location_count), dtype=float)
        for row, origin in enumerate(range(start, stop)):
            origin_stations = nearest[origin]
            best_to_station = np.min(
                nearest_access[origin, :, None]
                + network_minutes[origin_stations, :],
                axis=0,
            )
            network_route = np.min(
                best_to_station[nearest] + nearest_access,
                axis=1,
            )
            routed[row] = np.minimum(direct_minutes[origin], network_route)
        return start, routed

    if worker_count == 1:
        routed_blocks = map(route_block, blocks)
        for start, routed in progress_range(
            routed_blocks, total=len(blocks),
            description=f"TTMATRIX {label}: route origins", unit="block"
        ):
            result[start:start + len(routed)] = routed
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            routed_blocks = executor.map(route_block, blocks)
            for start, routed in progress_range(
                routed_blocks, total=len(blocks),
                description=f"TTMATRIX {label}: route origins", unit="block"
            ):
                result[start:start + len(routed)] = routed

    # Symmetric speeds and networks imply a symmetric matrix. Averaging removes
    # only floating-point ordering noise and makes CSV comparisons reproducible.
    result = 0.5 * (result + result.T)
    return result, int(len(stations))


def _travel_matrix_with_standalone_ttmatrix(
    direct_minutes: np.ndarray,
    centroid_coords: np.ndarray,
    network_path: Path,
    station_path: Path,
    routing_crs,
    offnetwork_speed: float,
    network_speed: float,
    label: str,
    settings: dict[str, Any],
) -> tuple[np.ndarray, int, dict[str, Any]]:
    """Route one scenario with the public standalone TTMATRIX graph method."""
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

    graph, graph_report = build_standalone_graph(
        centroid_coords,
        network,
        stations,
        walking_speed_kmh=offnetwork_speed,
        network_speed_kmh=network_speed,
        snap_tolerance_metres=float(settings.get("snap_tolerance_m", 1.0)),
        station_split_buffer_metres=float(settings.get("station_split_buffer_m", 0.5)),
        point_station_neighbours=int(settings.get("point_station_neighbors", 3)),
        point_walking_neighbours=int(settings.get("point_walking_neighbors", 5)),
        station_connector_minutes=float(settings.get("station_connector_minutes", 0.0001)),
    )
    matrix, path_report = standalone_shortest_path_matrix(
        graph,
        len(centroid_coords),
        label,
        workers=int(settings.get("workers", 1)),
    )
    unreachable_pairs = int((~np.isfinite(matrix)).sum())
    if unreachable_pairs and settings.get("unreachable_rule", "stop") == "stop":
        raise MatrixInputError(
            f"Standalone TTMATRIX left {unreachable_pairs} {label} OD pairs "
            "unreachable. This can arise from disconnected walking components; "
            "inspect the network or increase ttmatrix.point_walking_neighbors."
        )

    # Sparse walking links can create detours relative to straight-line travel.
    valid = np.isfinite(matrix) & (direct_minutes > 0)
    detour_ratios = matrix[valid] / direct_minutes[valid]
    detour_warning_ratio = float(settings.get("detour_warning_ratio", 2.0))
    diagnostics = {
        **graph_report,
        **path_report,
        "detour_ratio_p99": float(np.quantile(detour_ratios, 0.99)) if detour_ratios.size else 1.0,
        "detour_ratio_max": float(detour_ratios.max()) if detour_ratios.size else 1.0,
        "detour_warning_ratio": detour_warning_ratio,
        "detour_warning_pairs": int((detour_ratios > detour_warning_ratio).sum()),
    }
    return matrix, int(len(stations)), diagnostics


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
    routing_method = str(tt_cfg.get("routing_method", "standalone_ttmatrix")).lower()
    if routing_method not in {"standalone_ttmatrix", "legacy_access_network_egress"}:
        raise MatrixInputError(
            "ttmatrix.routing_method must be standalone_ttmatrix or "
            "legacy_access_network_egress."
        )
    configured_candidates = tt_cfg.get(
        "legacy_station_candidates", tt_cfg.get("station_candidates", "all")
    )
    station_candidates = None if str(configured_candidates).lower() == "all" else int(configured_candidates)
    if station_candidates is not None and station_candidates < 1:
        raise MatrixInputError(
            "ttmatrix.legacy_station_candidates must be a positive integer or 'all'."
        )
    configured_workers = tt_cfg.get("workers", 1)
    workers = min(os.cpu_count() or 1, 8) if str(configured_workers).lower() == "auto" else int(configured_workers)
    if workers < 1:
        raise MatrixInputError("ttmatrix.workers must be a positive integer or 'auto'.")
    routing_settings = dict(tt_cfg)
    routing_settings["workers"] = workers
    direct_started = perf_counter()
    direct_distance = cdist(coords, coords)
    direct_minutes = direct_distance / (offnetwork_speed * 1000.0 / 60.0)
    direct_seconds = perf_counter() - direct_started

    # Null baseline paths mean no initial transport network. The standalone
    # method uses its walking graph; the legacy method uses direct distances.
    baseline_network = config["paths"].get("baseline_network")
    baseline_stations = config["paths"].get("baseline_stations")
    baseline_started = perf_counter()
    baseline_routing_diagnostics: dict[str, Any] = {"network_supplied": False}
    if baseline_network and baseline_stations:
        if routing_method == "standalone_ttmatrix":
            baseline, baseline_station_count, baseline_routing_diagnostics = (
                _travel_matrix_with_standalone_ttmatrix(
                    direct_minutes, coords, Path(baseline_network), Path(baseline_stations),
                    routing_crs, offnetwork_speed, network_speed, "baseline", routing_settings,
                )
            )
            baseline_definition = "standalone TTMATRIX augmented-graph shortest paths"
        else:
            baseline, baseline_station_count = _travel_matrix_with_network_legacy(
                direct_minutes, coords, Path(baseline_network), Path(baseline_stations),
                routing_crs, offnetwork_speed, network_speed, "baseline",
                station_candidates, workers,
            )
            baseline_routing_diagnostics = {"network_supplied": True}
            baseline_definition = "legacy direct-or-access-network-egress minimum"
    else:
        if routing_method == "standalone_ttmatrix":
            walking_graph, graph_report = build_standalone_walking_graph(
                coords,
                offnetwork_speed,
                point_walking_neighbours=int(tt_cfg.get("point_walking_neighbors", 5)),
            )
            baseline, path_report = standalone_shortest_path_matrix(
                walking_graph, len(coords), "baseline", workers=workers
            )
            baseline_routing_diagnostics = {**graph_report, **path_report}
            if path_report["unreachable_pairs"] and tt_cfg.get("unreachable_rule", "stop") == "stop":
                raise MatrixInputError(
                    f"Standalone TTMATRIX left {path_report['unreachable_pairs']} baseline "
                    "OD pairs unreachable. Increase ttmatrix.point_walking_neighbors."
                )
            baseline_valid = np.isfinite(baseline) & (direct_minutes > 0)
            baseline_detours = baseline[baseline_valid] / direct_minutes[baseline_valid]
            detour_warning_ratio = float(tt_cfg.get("detour_warning_ratio", 2.0))
            baseline_routing_diagnostics.update({
                "detour_ratio_p99": float(np.quantile(baseline_detours, 0.99)),
                "detour_ratio_max": float(baseline_detours.max()),
                "detour_warning_ratio": detour_warning_ratio,
                "detour_warning_pairs": int(
                    (baseline_detours > detour_warning_ratio).sum()
                ),
            })
            baseline_definition = "standalone TTMATRIX nearest-neighbour walking graph"
        else:
            baseline = direct_minutes.copy()
            baseline_definition = "direct centroid-to-centroid travel without a baseline network"
        baseline_station_count = 0
    baseline_seconds = perf_counter() - baseline_started

    # Null counterfactual paths mean no transport intervention. Reuse the
    # complete baseline matrix, whether the baseline is direct travel or was
    # constructed from an initial network. This permits fundamentals-only
    # counterfactuals without introducing a spurious network change.
    counterfactual_network = config["paths"].get("counterfactual_network")
    counterfactual_stations = config["paths"].get("counterfactual_stations")
    counterfactual_started = perf_counter()
    counterfactual_routing_diagnostics: dict[str, Any] = {"network_supplied": False}
    if counterfactual_network and counterfactual_stations:
        if routing_method == "standalone_ttmatrix":
            counterfactual, counterfactual_station_count, counterfactual_routing_diagnostics = (
                _travel_matrix_with_standalone_ttmatrix(
                    direct_minutes, coords, Path(counterfactual_network),
                    Path(counterfactual_stations), routing_crs, offnetwork_speed,
                    network_speed, "counterfactual", routing_settings,
                )
            )
            counterfactual_definition = "standalone TTMATRIX augmented-graph shortest paths"
        else:
            counterfactual, counterfactual_station_count = _travel_matrix_with_network_legacy(
                direct_minutes, coords, Path(counterfactual_network),
                Path(counterfactual_stations), routing_crs, offnetwork_speed,
                network_speed, "counterfactual", station_candidates, workers,
            )
            counterfactual_routing_diagnostics = {"network_supplied": True}
            counterfactual_definition = "legacy direct-or-access-network-egress minimum"
    else:
        counterfactual = baseline.copy()
        counterfactual_station_count = baseline_station_count
        counterfactual_definition = "identical to baseline travel (no transport intervention)"
    counterfactual_seconds = perf_counter() - counterfactual_started

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
        "routing_method": routing_method,
        "legacy_station_candidates": "all" if station_candidates is None else station_candidates,
        "workers": workers,
        "direct_matrix_seconds": direct_seconds,
        "baseline_routing_seconds": baseline_seconds,
        "counterfactual_routing_seconds": counterfactual_seconds,
        "baseline_routing": baseline_routing_diagnostics,
        "counterfactual_routing": counterfactual_routing_diagnostics,
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
