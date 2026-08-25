"""01: invert the model-consistent baseline and save reusable fundamentals."""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

from functions.inversion import invert_baseline
from functions.io import load_config, output_dir, read_inputs, read_matrix
from functions.types import Parameters


def run(project_root: Path):
    config = load_config(project_root)
    param = Parameters.from_config(config)
    data = read_inputs(project_root)
    travel_time = read_matrix(project_root, "travel_times_baseline.csv", data.n)
    inversion = invert_baseline(data, travel_time, param)
    if not inversion.converged:
        raise RuntimeError(f"Baseline inversion did not balance: {inversion.diagnostics}")
    destination = output_dir(project_root, config, "inversion")
    with (destination / "baseline_inversion.pkl").open("wb") as stream:
        pickle.dump({"config": config, "parameters": param, "data": data, "inversion": inversion}, stream)
    pd.DataFrame({
        "location_id": data.ids,
        "fundamental_productivity": inversion.fundamentals.productivity,
        "fundamental_amenity": inversion.fundamentals.amenity,
        "structural_density": inversion.fundamentals.density,
        "wage": inversion.wage,
        "commercial_floor_share": inversion.commercial_share,
    }).to_csv(destination / "inverted_primitives.csv", index=False)
    print(f"Baseline inversion converged in {inversion.iterations} balancing iterations.")
    return config, param, data, inversion


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[3])
