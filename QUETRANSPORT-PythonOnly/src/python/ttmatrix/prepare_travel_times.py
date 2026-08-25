"""Validate, align, convert, and export baseline/counterfactual travel matrices."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common.identifiers import canonical_id, canonical_series


class MatrixInputError(ValueError):
    """Raised when an OD matrix violates the standardized contract."""


def _read_matrix(path: Path, ids: list[str], label: str) -> pd.DataFrame:
    if not path.is_file():
        raise MatrixInputError(f"{label} matrix not found: {path}")
    matrix = pd.read_csv(path, index_col=0)
    matrix.index = [canonical_id(value) for value in matrix.index]
    matrix.columns = [canonical_id(value) for value in matrix.columns]
    if matrix.index.duplicated().any() or matrix.columns.duplicated().any():
        raise MatrixInputError(f"{label} matrix contains duplicate row or column IDs.")
    missing_rows = sorted(set(ids) - set(matrix.index))
    missing_cols = sorted(set(ids) - set(matrix.columns))
    extra_rows = sorted(set(matrix.index) - set(ids))
    extra_cols = sorted(set(matrix.columns) - set(ids))
    if missing_rows or missing_cols or extra_rows or extra_cols:
        raise MatrixInputError(
            f"{label} IDs differ from locations.csv. "
            f"Missing rows={missing_rows[:5]}, missing columns={missing_cols[:5]}, "
            f"extra rows={extra_rows[:5]}, extra columns={extra_cols[:5]}."
        )
    matrix = matrix.loc[ids, ids].apply(pd.to_numeric, errors="coerce")
    values = matrix.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise MatrixInputError(f"{label} matrix contains missing or infinite values.")
    if (values < 0).any():
        raise MatrixInputError(f"{label} matrix contains negative travel times.")
    return matrix


def _to_minutes(matrix: pd.DataFrame, unit: str) -> pd.DataFrame:
    if unit == "minutes":
        return matrix
    if unit == "seconds":
        return matrix / 60.0
    if unit == "hours":
        return matrix * 60.0
    raise MatrixInputError(f"Unsupported travel-time unit: {unit}")


def prepare_travel_times(config: dict[str, Any]) -> dict[str, Any]:
    input_root = Path(config["paths"]["standardized_input"])
    locations_path = input_root / "model" / "locations.csv"
    if not locations_path.is_file():
        raise MatrixInputError(f"Run GRID standardization first; missing {locations_path}")
    locations = pd.read_csv(locations_path, dtype={"location_id": "string"})
    ids = canonical_series(locations["location_id"]).tolist()

    baseline = _read_matrix(Path(config["paths"]["baseline_matrix"]), ids, "Baseline")
    counterfactual = _read_matrix(Path(config["paths"]["counterfactual_matrix"]), ids, "Counterfactual")
    unit = config["ttmatrix"]["time_unit"]
    baseline = _to_minutes(baseline, unit)
    counterfactual = _to_minutes(counterfactual, unit)

    diagonal_rule = config["ttmatrix"].get("intrazonal_rule", "keep")
    if diagonal_rule == "configured_constant":
        diagonal = float(config["ttmatrix"].get("intrazonal_minutes", 0.0))
        baseline_values = baseline.to_numpy(dtype=float, copy=True)
        counterfactual_values = counterfactual.to_numpy(dtype=float, copy=True)
        np.fill_diagonal(baseline_values, diagonal)
        np.fill_diagonal(counterfactual_values, diagonal)
        baseline = pd.DataFrame(baseline_values, index=baseline.index, columns=baseline.columns)
        counterfactual = pd.DataFrame(counterfactual_values, index=counterfactual.index, columns=counterfactual.columns)
    elif diagonal_rule != "keep":
        raise MatrixInputError("ttmatrix.intrazonal_rule must be keep or configured_constant.")

    matrix_dir = input_root / "travel_times"
    diagnostics_dir = Path(config["paths"]["output"]) / "diagnostics"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    baseline.index.name = "location_id"
    counterfactual.index.name = "location_id"
    baseline.columns = [f"location_id_{value}" for value in ids]
    counterfactual.columns = baseline.columns
    baseline.to_csv(matrix_dir / "travel_times_baseline.csv")
    counterfactual.to_csv(matrix_dir / "travel_times_counterfactual.csv")

    b = baseline.to_numpy(dtype=float)
    c = counterfactual.to_numpy(dtype=float)
    correlation = float(np.corrcoef(b.ravel(), c.ravel())[0, 1])
    difference = c - b
    report = {
        "number_of_locations": len(ids),
        "unit_exported": "minutes",
        "baseline_minimum": float(b.min()),
        "baseline_mean": float(b.mean()),
        "baseline_maximum": float(b.max()),
        "counterfactual_minimum": float(c.min()),
        "counterfactual_mean": float(c.mean()),
        "counterfactual_maximum": float(c.max()),
        "matrix_correlation": correlation,
        "improved_pairs": int((difference < -1e-10).sum()),
        "unchanged_pairs": int((np.abs(difference) <= 1e-10).sum()),
        "slower_pairs": int((difference > 1e-10).sum()),
    }
    (diagnostics_dir / "travel_time_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
