"""Interpolate optional polygon-level primitive changes to model locations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from common.identifiers import canonical_series
from common.progress import progress_range


class ScenarioInputError(ValueError):
    """Raised when an optional primitive-shock geography violates the contract."""


# Standardized names read by MATLAB and their user-configurable source fields.
SHOCK_DEFINITIONS = (
    ("productivity_hat", "productivity_hat_variable"),
    ("amenity_hat", "amenity_hat_variable"),
    ("structural_density_hat", "structural_density_hat_variable"),
)


def _projected_crs(target: gpd.GeoDataFrame, configured: str | None):
    """Choose a projected metre CRS in which polygon areas are meaningful."""
    if configured:
        candidate = target.to_crs(configured).crs
        if candidate.is_geographic:
            raise ScenarioInputError("scenario.analysis_crs must use projected metre coordinates.")
        return candidate
    candidate = target.estimate_utm_crs()
    if candidate is None:
        raise ScenarioInputError("Could not infer a projected CRS; set scenario.analysis_crs.")
    return candidate


def prepare_primitive_shocks(config: dict[str, Any]) -> dict[str, Any]:
    """Area-interpolate arbitrary policy polygons onto the generated model grid.

    Source values are multiplicative hats. For each target model cell, the
    overlap-area-weighted deviation from one is summed and uncovered area is
    assigned the neutral value one. Consequently, a policy polygon covering
    25 percent of a cell with a hat of 1.20 produces a target-cell hat of 1.05.
    """
    standardized = Path(config["paths"]["standardized_input"])
    locations_file = standardized / "model" / "locations.csv"
    geography_file = standardized / "geography" / "locations.gpkg"
    shocks_dir = standardized / "shocks"
    standardized_file = shocks_dir / "shocks.csv"
    standardized_geography = shocks_dir / "shocks.gpkg"
    diagnostics_file = Path(config["paths"]["output"]) / "diagnostics" / "shock_interpolation.json"
    shocks_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_file.parent.mkdir(parents=True, exist_ok=True)

    if not locations_file.is_file() or not geography_file.is_file():
        raise ScenarioInputError("GRID must create locations.csv and locations.gpkg before shocks are prepared.")
    locations = pd.read_csv(locations_file, dtype={"location_id": "string"})
    location_id = canonical_series(locations["location_id"])
    target = gpd.read_file(geography_file, layer="locations")
    if "location_id" not in target.columns:
        raise ScenarioInputError("Standardized model geography has no location_id field.")
    target["location_id"] = canonical_series(target["location_id"])
    target = target.set_index("location_id").reindex(location_id.tolist()).reset_index()
    if target.geometry.isna().any():
        raise ScenarioInputError("Standardized model geography does not match locations.csv.")

    scenario = config.get("scenario", {})
    source_path = scenario.get("shocks_shapefile")
    if not source_path:
        # These are generated artifacts. Removing stale versions guarantees
        # that null always means a pure transport counterfactual.
        for path in (standardized_file, standardized_geography, diagnostics_file):
            if path.exists():
                path.unlink()
        return {
            "active": False,
            "source_file": None,
            "standardized_file": None,
            "standardized_geography": None,
            "changed_locations": 0,
        }

    source_path = Path(source_path)
    if not source_path.is_file():
        raise ScenarioInputError(f"Configured primitive-shock shapefile not found: {source_path}")
    layer = scenario.get("shocks_layer")
    source = gpd.read_file(source_path, layer=layer) if layer else gpd.read_file(source_path)
    if source.empty:
        raise ScenarioInputError("Primitive-shock geography contains no features.")
    if source.crs is None:
        raise ScenarioInputError("Primitive-shock geography has no coordinate reference system.")
    if not source.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ScenarioInputError("Primitive shocks must be supplied as polygons or multipolygons.")
    if not source.geometry.is_valid.all():
        source["geometry"] = source.geometry.make_valid()

    field_map: dict[str, str] = {}
    for standardized_name, config_name in SHOCK_DEFINITIONS:
        source_name = scenario.get(config_name)
        if source_name in (None, ""):
            continue
        if source_name not in source.columns:
            raise ScenarioInputError(
                f"Configured shock field '{source_name}' for {standardized_name} was not found."
            )
        values = pd.to_numeric(source[source_name], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all() or (values <= 0).any():
            raise ScenarioInputError(
                f"Shock field '{source_name}' must be finite and strictly positive in every polygon."
            )
        source[source_name] = values.astype(float)
        field_map[standardized_name] = source_name
    if not field_map:
        raise ScenarioInputError("At least one primitive-shock field must be configured.")

    analysis_crs = _projected_crs(target, scenario.get("analysis_crs"))
    target_projected = target.to_crs(analysis_crs).copy()
    source_projected = source.to_crs(analysis_crs).copy()
    target_projected["_target_area"] = target_projected.geometry.area
    if (target_projected["_target_area"] <= 0).any():
        raise ScenarioInputError("Model geography contains a zero-area cell.")

    # Reject positive-area overlaps among policy polygons. Boundary contacts
    # are harmless; containment and duplicate geometries are genuine overlaps.
    indexed_source = source_projected[["geometry"]].copy()
    indexed_source["_policy_id"] = np.arange(len(indexed_source), dtype=np.int64)
    pairs = gpd.sjoin(indexed_source, indexed_source, how="inner", predicate="intersects")
    pairs = pairs.loc[pairs["_policy_id_left"] < pairs["_policy_id_right"]]
    if not pairs.empty:
        left = gpd.GeoSeries(
            indexed_source.geometry.loc[pairs.index].to_numpy(),
            index=pairs.index,
            crs=analysis_crs,
        )
        right = gpd.GeoSeries(
            indexed_source.set_index("_policy_id").geometry.loc[pairs["_policy_id_right"]].to_numpy(),
            index=pairs.index,
            crs=analysis_crs,
        )
        if (left.intersection(right, align=False).area > 1.0e-8).any():
            raise ScenarioInputError(
                "Primitive-shock polygons overlap one another with positive area."
            )

    # Candidate pairs are found spatially; exact positive intersection areas
    # are then calculated in chunks so large policy layers remain transparent.
    candidates = gpd.sjoin(
        source_projected[[*field_map.values(), "geometry"]],
        target_projected[["location_id", "geometry"]],
        how="inner",
        predicate="intersects",
    )
    if candidates.empty:
        raise ScenarioInputError("Primitive-shock polygons do not intersect the model geography.")

    parts: list[pd.DataFrame] = []
    chunk_size = 50_000
    target_geometry = target_projected.set_index("location_id").geometry
    starts = range(0, len(candidates), chunk_size)
    for start in progress_range(
        starts,
        total=max(1, (len(candidates) + chunk_size - 1) // chunk_size),
        description="SHOCK overlap areas",
        unit="chunk",
    ):
        chunk = candidates.iloc[start:start + chunk_size].copy()
        if chunk.empty:
            continue
        right = gpd.GeoSeries(
            target_geometry.loc[chunk["location_id"]].to_numpy(),
            index=chunk.index,
            crs=analysis_crs,
        )
        chunk["_overlap_area"] = chunk.geometry.intersection(right, align=False).area
        chunk = chunk.loc[chunk["_overlap_area"] > 0]
        parts.append(pd.DataFrame(chunk.drop(columns=["geometry", "index_right"], errors="ignore")))

    output = pd.DataFrame({"location_id": location_id})
    target_area = target_projected.set_index("location_id")["_target_area"]
    if parts:
        overlaps = pd.concat(parts, ignore_index=True)
        coverage_area = overlaps.groupby("location_id")["_overlap_area"].sum()
        coverage_share = coverage_area / target_area.loc[coverage_area.index]
        if (coverage_share > 1.000001).any():
            bad = coverage_share.idxmax()
            raise ScenarioInputError(
                "Primitive-shock polygons overlap each other within the model geography; "
                f"coverage exceeds 100% in location {bad}."
            )
        coverage = output["location_id"].map(coverage_share).fillna(0.0).clip(0.0, 1.0)
        for standardized_name, source_name in field_map.items():
            contribution = (
                (overlaps[source_name] - 1.0) * overlaps["_overlap_area"]
            ).groupby(overlaps["location_id"]).sum()
            delta = output["location_id"].map(contribution).fillna(0.0)
            area = output["location_id"].map(target_area)
            output[standardized_name] = 1.0 + delta / area
    else:
        coverage = pd.Series(0.0, index=output.index)
        for standardized_name in field_map:
            output[standardized_name] = 1.0

    # A non-configured primitive remains fixed everywhere.
    for standardized_name, _ in SHOCK_DEFINITIONS:
        if standardized_name not in output.columns:
            output[standardized_name] = 1.0
    output = output[["location_id", *(name for name, _ in SHOCK_DEFINITIONS)]]
    if (output.iloc[:, 1:] <= 0).any().any():
        raise ScenarioInputError("Area interpolation produced a nonpositive primitive hat.")
    output.to_csv(standardized_file, index=False)

    mapped = target[["location_id", "geometry"]].merge(output, on="location_id", how="left")
    if standardized_geography.exists():
        standardized_geography.unlink()
    mapped.to_file(standardized_geography, layer="shocks", driver="GPKG")

    changed = ~np.isclose(output.iloc[:, 1:].to_numpy(), 1.0).all(axis=1)
    report = {
        "active": True,
        "source_file": str(source_path),
        "source_features": int(len(source)),
        "analysis_crs": str(analysis_crs),
        "field_map": field_map,
        "candidate_intersections": int(len(candidates)),
        "positive_area_intersections": int(sum(len(part) for part in parts)),
        "mean_target_coverage_share": float(coverage.mean()),
        "maximum_target_coverage_share": float(coverage.max()),
        "changed_locations": int(changed.sum()),
        "standardized_file": str(standardized_file),
        "standardized_geography": str(standardized_geography),
        "uncovered_area_rule": "neutral_hat_one",
    }
    diagnostics_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report