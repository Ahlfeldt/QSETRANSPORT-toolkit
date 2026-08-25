"""Run inversion, main counterfactuals, and the optional no-spillover comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from functions.io import load_config, output_dir
from scripts.invert_baseline import run as run_inversion
from scripts.run_counterfactual import run as run_counterfactual
from scripts.run_no_spillovers import run as run_no_spillovers


def run(project_root: Path) -> pd.DataFrame:
    config = load_config(project_root)
    run_inversion(project_root)
    main = run_counterfactual(project_root)
    if config["project"].get("run_no_spillover_comparison", False):
        sensitivity = run_no_spillovers(project_root)
        combined = pd.concat([main, sensitivity], ignore_index=True)
    else:
        combined = main
    combined.to_csv(output_dir(project_root, config, "simulation") / "aggregate_changes.csv", index=False)
    print("\n" + combined.to_string(index=False))
    return combined


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[3])
