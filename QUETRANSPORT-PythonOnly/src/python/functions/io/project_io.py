"""Read the standardized data contract and the single YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from ..types import ModelData


def load_config(project_root: Path) -> dict[str, Any]:
    path = project_root / "project_config.yaml"
    with path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    return config


def read_inputs(project_root: Path) -> ModelData:
    path = project_root / "input" / "standardized" / "model" / "locations.csv"
    table = pd.read_csv(path, dtype={"location_id": str})
    required = {"location_id", "population", "employment_model", "rent_floor_space", "land_area"}
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"locations.csv is missing: {sorted(missing)}")
    if table["location_id"].duplicated().any():
        raise ValueError("location_id must be unique")
    population = table["population"].to_numpy(float)
    employment = table["employment_model"].to_numpy(float)
    rent = table["rent_floor_space"].to_numpy(float)
    land_area = table["land_area"].to_numpy(float)
    if np.any(~np.isfinite(rent)) or np.any(rent <= 0):
        raise ValueError("Floor-space rents must be finite and positive")
    if not np.isclose(population.sum(), employment.sum(), rtol=1e-6, atol=1e-6):
        raise ValueError("Aggregate employment must equal aggregate population")
    return ModelData(table, table["location_id"].to_numpy(str), population, employment, rent, land_area)


def read_matrix(project_root: Path, filename: str, n: int) -> np.ndarray:
    path = project_root / "input" / "standardized" / "travel_times" / filename
    # Standard QUETRANSPORT matrices carry destination IDs in the header and
    # origin IDs in the first column. Retaining labels in the file makes OD
    # alignment inspectable; the model consumes only the numeric N-by-N block.
    labeled = pd.read_csv(path, index_col=0)
    matrix = labeled.to_numpy(float)
    if matrix.shape != (n, n):
        raise ValueError(f"{filename} has shape {matrix.shape}; expected {(n, n)}")
    if np.any(~np.isfinite(matrix)) or np.any(matrix < 0):
        raise ValueError(f"{filename} contains invalid travel times")
    return matrix


def output_dir(project_root: Path, config: dict[str, Any], stage: str) -> Path:
    root = Path(config.get("paths", {}).get("output", "outputs"))
    if not root.is_absolute():
        root = project_root / root
    path = root / stage
    path.mkdir(parents=True, exist_ok=True)
    return path
