"""03: re-invert and rerun with productivity and amenity spillovers set to zero."""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

from functions.inversion import invert_baseline
from functions.io import load_config, output_dir, read_inputs, read_matrix
from functions.types import Parameters
from scripts.run_counterfactual import run as run_counterfactual


def run(project_root: Path) -> pd.DataFrame:
    config = load_config(project_root)
    config["model"]["productivity_spillover"] = 0.0
    config["model"]["amenity_spillover"] = 0.0
    param = Parameters.from_config(config)
    data = read_inputs(project_root)
    baseline_time = read_matrix(project_root, "travel_times_baseline.csv", data.n)
    inversion = invert_baseline(data, baseline_time, param)
    main_dir = output_dir(project_root, config, "inversion")
    main_path = main_dir / "baseline_inversion.pkl"
    backup = main_path.read_bytes() if main_path.exists() else None
    try:
        with main_path.open("wb") as stream:
            pickle.dump({"config": config, "parameters": param, "data": data, "inversion": inversion}, stream)
        result = run_counterfactual(project_root, "no_spillovers")
    finally:
        if backup is not None:
            main_path.write_bytes(backup)
    return result


if __name__ == "__main__":
    print(run(Path(__file__).resolve().parents[3]).to_string(index=False))
