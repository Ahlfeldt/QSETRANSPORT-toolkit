"""Generate the complete analysis grid and standardized model inputs from source layers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, box

from common.geospatial_io import write_geopackage
from common.identifiers import canonical_series
from common.progress import progress_range
from grid.prepare_grid_inputs import GridInputError


def _projected_crs(source: gpd.GeoDataFrame, configured: str | None):
    if configured:
        candidate = source.to_crs(configured).crs
        if candidate.is_geographic:
            raise GridInputError("grid.analysis_crs must use projected metre coordinates.")
        return candidate
    candidate = source.estimate_utm_crs()
    if candidate is None:
        raise GridInputError("Could not infer a projected CRS; set grid.analysis_crs.")
    return candidate


def _read_source_layers(folder: Path) -> gpd.GeoDataFrame:
    paths = sorted(folder.glob("*.shp")) + sorted(folder.glob("*.gpkg"))
    if not paths:
        raise GridInputError(f"No .shp or .gpkg source layers found in {folder}")
    layers = []
    reference_crs = None
    for path in progress_range(paths, total=len(paths), description="GRID source layers", unit="layer"):
        layer = gpd.read_file(path)
        if layer.crs is None:
            raise GridInputError(f"Source layer has no CRS: {path}")
        if not layer.geom_type.isin(["Polygon", "MultiPolygon"]).all():
            raise GridInputError(f"GRID source must contain polygons: {path}")
        if reference_crs is None:
            reference_crs = layer.crs
        else:
            layer = layer.to_crs(reference_crs)
        layer["_source_file"] = path.name
        layers.append(layer)
    return gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), crs=reference_crs)


def _make_square_grid(source: gpd.GeoDataFrame, source_projected: gpd.GeoDataFrame,
                      cell_size_m: float, crs) -> gpd.GeoDataFrame:
    """Reproduce the centered GRID-toolkit grid convention."""
    source_wgs84 = source.to_crs(4326)
    xmin_lon, ymin_lat, xmax_lon, ymax_lat = source_wgs84.total_bounds
    center_lon = (xmin_lon + xmax_lon) / 2.0
    center_lat = (ymin_lat + ymax_lat) / 2.0
    center = gpd.GeoSeries([Point(center_lon, center_lat)], crs=4326).to_crs(crs).iloc[0]
    xmin, ymin, xmax, ymax = source_projected.total_bounds
    number_columns = int((xmax - xmin) // cell_size_m) + 1
    number_rows = int((ymax - ymin) // cell_size_m) + 1
    x0 = center.x - number_columns * cell_size_m / 2.0
    y0 = center.y + number_rows * cell_size_m / 2.0
    polygons = []
    for row in range(number_rows):
        for column in range(number_columns):
            left = x0 + column * cell_size_m
            top = y0 - row * cell_size_m
            polygons.append(box(left, top - cell_size_m, left + cell_size_m, top))
    return gpd.GeoDataFrame({"grid_sequence": np.arange(1, len(polygons) + 1)}, geometry=polygons, crs=crs)


def _make_hexagon_grid(source: gpd.GeoDataFrame, source_projected: gpd.GeoDataFrame,
                       cell_size_m: float, crs) -> gpd.GeoDataFrame:
    """Create regular hexagons with the same target area as square cells."""
    # cell_size_m squared is the target cell area. Choosing the hexagon side
    # from that area makes square and hexagon resolutions directly comparable.
    side = np.sqrt(2.0 * cell_size_m**2 / (3.0 * np.sqrt(3.0)))
    horizontal_spacing = np.sqrt(3.0) * side
    vertical_spacing = 1.5 * side
    source_wgs84 = source.to_crs(4326)
    xmin_lon, ymin_lat, xmax_lon, ymax_lat = source_wgs84.total_bounds
    center_lon = (xmin_lon + xmax_lon) / 2.0
    center_lat = (ymin_lat + ymax_lat) / 2.0
    center = gpd.GeoSeries([Point(center_lon, center_lat)], crs=4326).to_crs(crs).iloc[0]
    xmin, ymin, xmax, ymax = source_projected.total_bounds
    number_columns = int(np.ceil((xmax - xmin) / horizontal_spacing)) + 3
    number_rows = int(np.ceil((ymax - ymin) / vertical_spacing)) + 3
    x0 = center.x - (number_columns - 1) * horizontal_spacing / 2.0
    y0 = center.y + (number_rows - 1) * vertical_spacing / 2.0
    polygons = []
    for row in range(number_rows):
        y = y0 - row * vertical_spacing
        offset = horizontal_spacing / 2.0 if row % 2 else 0.0
        for column in range(number_columns):
            x = x0 + column * horizontal_spacing + offset
            vertices = [
                (x + side * np.cos(np.deg2rad(30 + 60 * angle)),
                 y + side * np.sin(np.deg2rad(30 + 60 * angle)))
                for angle in range(6)
            ]
            polygons.append(Polygon(vertices))
    return gpd.GeoDataFrame(
        {"grid_sequence": np.arange(1, len(polygons) + 1)},
        geometry=polygons,
        crs=crs,
    )


def _area_interpolate(
    source: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    extensive_columns: list[str],
    intensive_columns: list[str],
    chunk_size: int = 50_000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attribute source data by polygon overlap rather than intersection count.

    Extensive variables (population and employment) are allocated in proportion
    to the share of each source polygon covered by a target cell, then summed.
    This preserves totals. Intensive variables (the common rent and developed shares)
    receive a true intersection-area-weighted mean.
    """
    requested = list(dict.fromkeys(extensive_columns + intensive_columns))
    missing = [name for name in requested if name not in source.columns]
    if missing:
        raise GridInputError(
            "Source GRID layers do not contain configured variable(s): "
            + ", ".join(missing)
        )

    work = source[requested + ["geometry"]].copy()
    work["_source_id"] = np.arange(len(work), dtype=np.int64)
    work["_source_area"] = work.geometry.area
    if (work["_source_area"] <= 0).any():
        raise GridInputError("GRID source contains polygon features with zero area.")
    for name in requested:
        work[name] = pd.to_numeric(work[name], errors="coerce")

    # The spatial join finds only candidate polygon pairs. Exact intersection
    # areas are then evaluated in manageable chunks with a visible progress bar.
    candidates = gpd.sjoin(
        work,
        grid[["grid_sequence", "geometry"]],
        how="inner",
        predicate="intersects",
    )
    if candidates.empty:
        raise GridInputError("No source polygon intersects the generated analysis grid.")

    target_geometry = grid.set_index("grid_sequence").geometry
    parts: list[pd.DataFrame] = []
    starts = range(0, len(candidates), chunk_size)
    for start in progress_range(
        starts,
        total=(len(candidates) + chunk_size - 1) // chunk_size,
        description="GRID overlap areas",
        unit="chunk",
    ):
        chunk = candidates.iloc[start:start + chunk_size].copy()
        right = gpd.GeoSeries(
            target_geometry.loc[chunk["grid_sequence"]].to_numpy(),
            index=chunk.index,
            crs=grid.crs,
        )
        chunk["_overlap_area"] = chunk.geometry.intersection(right, align=False).area
        chunk = chunk.loc[chunk["_overlap_area"] > 0]
        parts.append(pd.DataFrame(chunk.drop(columns=["geometry", "index_right"], errors="ignore")))

    overlaps = pd.concat(parts, ignore_index=True)
    result = pd.DataFrame({"grid_sequence": grid["grid_sequence"].to_numpy()})

    for name in extensive_columns:
        contribution = (
            overlaps[name].fillna(0.0)
            * overlaps["_overlap_area"]
            / overlaps["_source_area"]
        )
        allocated = contribution.groupby(overlaps["grid_sequence"]).sum()
        result[name] = result["grid_sequence"].map(allocated).fillna(0.0)

    for name in intensive_columns:
        valid = overlaps[name].notna()
        numerator = (
            overlaps.loc[valid, name] * overlaps.loc[valid, "_overlap_area"]
        ).groupby(overlaps.loc[valid, "grid_sequence"]).sum()
        denominator = overlaps.loc[valid].groupby("grid_sequence")["_overlap_area"].sum()
        weighted = numerator / denominator
        result[name] = result["grid_sequence"].map(weighted)

    diagnostics: dict[str, Any] = {
        "interpolation": "intersection_area",
        "candidate_intersections": int(len(candidates)),
        "positive_area_intersections": int(len(overlaps)),
        "extensive_variables": extensive_columns,
        "intensive_variables": intensive_columns,
    }
    for name in extensive_columns:
        source_total = float(work[name].fillna(0.0).sum())
        allocated_total = float(result[name].sum())
        diagnostics[f"{name}_source_total"] = source_total
        diagnostics[f"{name}_allocated_total"] = allocated_total
        diagnostics[f"{name}_allocation_ratio"] = (
            allocated_total / source_total if source_total != 0 else None
        )
    return result, diagnostics

def _positive_replace(values: pd.Series, name: str) -> pd.Series:
    result = pd.to_numeric(values, errors="coerce").fillna(0.0).clip(lower=0.0)
    positive = result[result > 0]
    if positive.empty:
        raise GridInputError(f"No positive values found for {name} in retained cells.")
    return result.mask(result == 0, positive.min())


def generate_grid_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Reproduce the cumulative GRID workflow from raw source polygons."""
    source_folder = Path(config["paths"]["source_grid_folder"])
    output_root = Path(config["paths"]["standardized_input"])
    model_dir = output_root / "model"
    geography_dir = output_root / "geography"
    diagnostics_dir = Path(config["paths"]["output"]) / "diagnostics"
    for directory in (model_dir, geography_dir, diagnostics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source = _read_source_layers(source_folder)
    grid_cfg = config["grid"]
    analysis_crs = _projected_crs(source, grid_cfg.get("analysis_crs"))
    source_projected = source.to_crs(analysis_crs)
    cell_geometry = str(grid_cfg.get("cell_geometry", "square")).lower()
    cell_size_m: float | None = None
    if cell_geometry in {"square", "hexagon"}:
        cell_size_m = float(grid_cfg["cell_size_km"]) * 1000.0
        if cell_size_m <= 0:
            raise GridInputError("grid.cell_size_km must be positive.")
    if cell_geometry == "square":
        grid = _make_square_grid(source, source_projected, cell_size_m, analysis_crs)
    elif cell_geometry == "hexagon":
        grid = _make_hexagon_grid(source, source_projected, cell_size_m, analysis_crs)
    elif cell_geometry == "original":
        # Preserve every supplied source polygon as one model location. Values
        # are still passed through the same area-interpolation interface, which
        # becomes an identity mapping for non-overlapping source polygons.
        grid = source_projected[["geometry"]].copy().reset_index(drop=True)
        grid["grid_sequence"] = np.arange(1, len(grid) + 1)
        original_id = grid_cfg.get("original_id_variable")
        if original_id:
            if original_id not in source.columns:
                raise GridInputError(
                    f"Configured original ID variable not found: {original_id}"
                )
            identifiers = canonical_series(source[original_id]).reset_index(drop=True)
            if identifiers.isna().any() or (identifiers == "").any():
                raise GridInputError("Original polygon identifiers cannot be missing.")
            if identifiers.duplicated().any():
                duplicates = identifiers[identifiers.duplicated()].head().tolist()
                raise GridInputError(f"Original polygon identifiers are not unique: {duplicates}")
            grid["_original_location_id"] = identifiers.to_numpy()
    else:
        raise GridInputError("grid.cell_geometry must be square, hexagon, or original.")
    grid_cells_before_filter = int(len(grid))

    # AREA-BASED ATTRIBUTION -------------------------------------------------
    # Population and employment are extensive quantities: each source total is
    # split across target cells according to the fraction of its polygon area
    # falling in each cell. The common rent and developed shares are intensive:
    # they receive an intersection-area-weighted mean. This avoids giving a
    # tiny corner intersection the same weight as a nearly complete overlap.
    pop_source = grid_cfg["population_source_variable"]
    emp_source = grid_cfg["employment_source_variable"]
    keep_source = grid_cfg.get("developed_source_variable")
    intensive_columns = [
        grid_cfg.get("developed_source_variable"),
        grid_cfg.get("rent_source_variable"),
    ]
    intensive_columns = [
        name for name in dict.fromkeys(intensive_columns)
        if name and name not in {pop_source, emp_source}
    ]
    numeric_columns = [pop_source, emp_source] + intensive_columns
    aggregated, interpolation_report = _area_interpolate(
        source_projected,
        grid,
        extensive_columns=[pop_source, emp_source],
        intensive_columns=intensive_columns,
    )
    grid = grid.merge(aggregated, on="grid_sequence", how="left")
    for column in numeric_columns:
        grid[column] = pd.to_numeric(grid[column], errors="coerce").fillna(0.0)
    if cell_geometry == "original":
        # Retaining the source units means retaining their complete polygon set;
        # downstream support rules, rather than a newly generated-grid filter,
        # determine whether a location hosts residents, employment, or both.
        keep = pd.Series(True, index=grid.index)
    else:
        keep = (grid[pop_source] > 0) | (grid[emp_source] > 0)
        if keep_source:
            if keep_source not in grid.columns:
                raise GridInputError(f"Source GRID layers do not contain '{keep_source}'.")
            keep = keep | (grid[keep_source] > 0)
    grid = grid.loc[keep].copy()
    if grid.empty:
        raise GridInputError("GRID filtering retained no analysis cells.")
    if cell_geometry == "original" and "_original_location_id" in grid.columns:
        grid["location_id"] = grid["_original_location_id"]
    else:
        grid["location_id"] = grid["grid_sequence"].astype(str)

    pop_weight = _positive_replace(grid[pop_source], pop_source)
    emp_weight = _positive_replace(grid[emp_source], emp_source)
    total_population = float(grid_cfg["total_population"])
    population = pop_weight / pop_weight.sum() * total_population
    employment_raw = emp_weight / emp_weight.sum() * total_population
    employment_scale = float(population.sum() / employment_raw.sum())
    employment_model = employment_raw * employment_scale

    rng = np.random.default_rng(int(grid_cfg.get("random_seed", 1)))
    # OPTION 1: the user supplies one observed baseline floor-space rent.
    # It is not a land rent and it is not interpreted as a regulatory wedge.
    # MATLAB passes this same observation into the commercial and residential
    # baseline inversion equations. The equilibrium solver nevertheless keeps
    # separate commercial and residential bid rents as endogenous outcomes.
    rent_source = grid_cfg.get("rent_source_variable")
    if rent_source:
        if rent_source not in grid.columns:
            raise GridInputError(f"Configured floor-space rent variable not found: {rent_source}")
        rent = _positive_replace(grid[rent_source], rent_source)
    else:
        exponent = float(grid_cfg.get("synthetic_rent_population_elasticity", grid_cfg.get("synthetic_rent_exponent", 0.25)))
        spread = float(grid_cfg.get("synthetic_rent_random_spread", 0.10))
        rent = population.pow(exponent) * rng.uniform(1-spread, 1+spread, len(grid))
    rent = rent / np.mean(rent)

    land_area = grid.geometry.area.to_numpy()
    locations = pd.DataFrame({
        "location_id": grid["location_id"].to_numpy(),
        "population": population.to_numpy(),
        "employment_raw": employment_raw.to_numpy(),
        "employment_model": employment_model.to_numpy(),
        "rent_floor_space": np.asarray(rent),
        "land_area": land_area,
    })
    locations.to_csv(model_dir / "locations.csv", index=False)

    polygons = grid[["location_id", "geometry"]].copy()
    centroids = polygons.copy()
    centroids["geometry"] = centroids.geometry.centroid
    centroids["lon"] = centroids.to_crs(4326).geometry.x
    centroids["lat"] = centroids.to_crs(4326).geometry.y
    output_crs = grid_cfg.get("output_crs") or "EPSG:4326"
    polygons_out = polygons.to_crs(output_crs)
    centroids_out = centroids.to_crs(output_crs)
    for path in (geography_dir / "locations.gpkg", geography_dir / "centroids.gpkg"):
        if path.exists():
            path.unlink()
    write_geopackage(polygons_out, geography_dir / "locations.gpkg", layer="locations")
    write_geopackage(centroids_out, geography_dir / "centroids.gpkg", layer="centroids")
    # Shapefile field names are limited to ten characters; use an explicit
    # loc_id alias while preserving location_id in the preferred GeoPackages.
    polygons_out.rename(columns={"location_id": "loc_id"}).to_file(geography_dir / "locations.shp")
    centroids_out.rename(columns={"location_id": "loc_id"}).to_file(geography_dir / "centroids.shp")

    report = {
        "mode": "generate_from_source_layers",
        "source_layers": sorted(path.name for path in source_folder.glob("*.shp")),
        "source_features": int(len(source)),
        "coarse_grid_cells_before_filter": grid_cells_before_filter,
        "number_of_locations": int(len(locations)),
        "cell_geometry": cell_geometry,
        "cell_size_km": None if cell_size_m is None else cell_size_m / 1000.0,
        "analysis_crs": str(analysis_crs),
        "output_crs": str(polygons_out.crs),
        "population_total": float(population.sum()),
        "employment_raw_total": float(employment_raw.sum()),
        "employment_scale_factor": employment_scale,
        "employment_model_total": float(employment_model.sum()),
        "synthetic_floor_space_rent": rent_source is None,
        "area_interpolation": interpolation_report,
    }
    (diagnostics_dir / "grid_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
