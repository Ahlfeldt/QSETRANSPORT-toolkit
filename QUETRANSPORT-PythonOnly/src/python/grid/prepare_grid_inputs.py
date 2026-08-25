"""Convert an existing GRID output into QUETRANSPORT's standardized inputs."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from common.identifiers import canonical_series


class GridInputError(ValueError):
    """Raised when GRID data and geometry cannot satisfy the data contract."""


def _numeric(source: pd.DataFrame, column: str, label: str) -> pd.Series:
    if column not in source.columns:
        raise GridInputError(f"GRID source does not contain {label} column '{column}'.")
    values = pd.to_numeric(source[column], errors="coerce")
    if values.isna().any():
        rows = list(source.index[values.isna()][:5] + 2)
        raise GridInputError(f"{label} has missing/non-numeric values near CSV rows {rows}.")
    return values.astype(float)



def prepare_grid_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Standardize locations and matching geometry; return a validation report."""
    source_csv = Path(config["paths"]["source_grid_csv"])
    source_geometry = Path(config["paths"]["source_grid_geometry"])
    output_root = Path(config["paths"]["standardized_input"])
    model_dir = output_root / "model"
    geography_dir = output_root / "geography"
    diagnostics_dir = Path(config["paths"]["output"]) / "diagnostics"
    for directory in (model_dir, geography_dir, diagnostics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    if not source_csv.is_file():
        raise GridInputError(f"GRID source CSV not found: {source_csv}")
    if not source_geometry.is_file():
        raise GridInputError(f"GRID source geometry not found: {source_geometry}")

    source = pd.read_csv(source_csv)
    mapping = config["grid"]
    id_name = mapping["id_variable"]
    if id_name not in source.columns:
        raise GridInputError(f"GRID source does not contain ID column '{id_name}'.")
    location_id = canonical_series(source[id_name])
    if location_id.duplicated().any():
        duplicates = location_id[location_id.duplicated()].head().tolist()
        raise GridInputError(f"Duplicate location identifiers in GRID CSV: {duplicates}")

    population = _numeric(source, mapping["population_variable"], "population")
    employment_raw = _numeric(source, mapping["employment_variable"], "employment")
    rent = _numeric(source, mapping["rent_variable"], "floor-space rent")
    if (population < 0).any() or population.sum() <= 0:
        raise GridInputError("Population must be nonnegative and positive in aggregate.")
    if (employment_raw < 0).any() or employment_raw.sum() <= 0:
        raise GridInputError("Employment must be nonnegative and positive in aggregate.")
    if (rent <= 0).any():
        raise GridInputError("The observed floor-space rent must be strictly positive everywhere.")

    employment_scale = float(population.sum() / employment_raw.sum())
    locations = pd.DataFrame({
        "location_id": location_id,
        "population": population,
        "employment_raw": employment_raw,
        "employment_model": employment_raw * employment_scale,
        "rent_floor_space": rent,
    })

    geometry = gpd.read_file(source_geometry)
    geometry_id_name = mapping.get("geometry_id_variable") or id_name
    if geometry_id_name not in geometry.columns:
        raise GridInputError(f"Geometry does not contain ID field '{geometry_id_name}'.")
    geometry["location_id"] = canonical_series(geometry[geometry_id_name])
    if geometry["location_id"].duplicated().any():
        raise GridInputError("Geometry contains duplicate location identifiers.")
    geometry = geometry.set_index("location_id").reindex(location_id.tolist())
    if geometry.geometry.isna().any():
        missing = geometry.index[geometry.geometry.isna()].tolist()[:5]
        raise GridInputError(f"Geometry is missing IDs from the CSV: {missing}")
    if not geometry.geometry.is_valid.all():
        geometry["geometry"] = geometry.geometry.make_valid()

    area_geometry = geometry
    if area_geometry.crs is None:
        raise GridInputError("Geometry has no CRS; land area cannot be computed safely.")
    if area_geometry.crs.is_geographic:
        estimated = area_geometry.estimate_utm_crs()
        if estimated is None:
            raise GridInputError("Could not select a projected CRS for land-area calculation.")
        area_geometry = area_geometry.to_crs(estimated)
    locations["land_area"] = area_geometry.geometry.area.to_numpy()
    if (locations["land_area"] <= 0).any():
        raise GridInputError("Every retained location must have positive land area.")
    locations.to_csv(model_dir / "locations.csv", index=False)

    geography = geometry.reset_index()[["location_id", "geometry"]]
    target_crs = mapping.get("target_crs")
    if target_crs:
        geography = geography.to_crs(target_crs)
    geography_path = geography_dir / "locations.gpkg"
    if geography_path.exists():
        geography_path.unlink()
    geography.to_file(geography_path, layer="locations", driver="GPKG")

    report = {
        "number_of_locations": int(len(locations)),
        "population_total": float(population.sum()),
        "employment_raw_total": float(employment_raw.sum()),
        "employment_scale_factor": employment_scale,
        "employment_model_total": float(locations["employment_model"].sum()),
        "geometry_crs": str(geography.crs),
        "rent_input_type": "one common observed baseline floor-space rent",
        "source_csv": str(source_csv),
        "source_geometry": str(source_geometry),
    }
    (diagnostics_dir / "grid_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
