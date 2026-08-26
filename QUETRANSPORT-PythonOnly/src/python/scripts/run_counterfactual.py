"""02: solve requested closures and write local and aggregate results."""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

from functions.equilibrium import apply_shocks, solve_closure, solve_fixed_distribution
from functions.io import load_config, output_dir, read_matrix
from functions.reporting import write_closure_results


def _closures(config: dict) -> list[str]:
    value = str(config["model"]["city_closure"]).lower()
    return ["closed", "open"] if value == "both" else [value]


def run(project_root: Path, specification: str = "with_spillovers") -> pd.DataFrame:
    config = load_config(project_root)
    inversion_path = output_dir(project_root, config, "inversion") / "baseline_inversion.pkl"
    with inversion_path.open("rb") as stream:
        stored = pickle.load(stream)
    param, data, inversion = stored["parameters"], stored["data"], stored["inversion"]
    baseline_time = read_matrix(project_root, "travel_times_baseline.csv", data.n)
    counterfactual_time = read_matrix(project_root, "travel_times_counterfactual.csv", data.n)
    fundamentals_cf = apply_shocks(project_root, data, inversion.fundamentals, config)
    rows, solved = [], {}
    specification_label = "Main" if specification == "with_spillovers" else "No spillovers"
    for closure in _closures(config):
        closure_label = closure.capitalize() + " city"
        baseline = solve_closure(
            closure, param, inversion.fundamentals, baseline_time,
            inversion.reservation_utility if closure == "open" else None,
            progress_label=f"[{specification_label} | Baseline | {closure_label}]",
        )
        counterfactual = solve_closure(
            closure, param, fundamentals_cf, counterfactual_time,
            inversion.reservation_utility if closure == "open" else None,
            progress_label=f"[{specification_label} | Counterfactual | {closure_label}]",
        )
        if not baseline.converged or not counterfactual.converged:
            raise RuntimeError(f"{closure}-city equilibrium failed to converge")
        rows.append(write_closure_results(
            project_root, data, baseline, counterfactual, baseline_time,
            counterfactual_time, config, param, specification,
        ))
        solved[closure] = (baseline, counterfactual)
    fixed_base = solved.get("closed", (None, None))[0]
    if fixed_base is None:
        fixed_base = solve_closure(
            "closed", param, inversion.fundamentals, baseline_time,
            progress_label=f"[{specification_label} | Baseline | Closed city]",
        )
    fixed_cf = solve_fixed_distribution(
        param, fundamentals_cf, baseline_time, counterfactual_time, fixed_base, data
    )
    rows.append(write_closure_results(
        project_root, data, fixed_base, fixed_cf, baseline_time,
        counterfactual_time, config, param, specification,
    ))
    if fixed_cf.welfare_components:
        pd.DataFrame([fixed_cf.welfare_components]).to_csv(
            output_dir(project_root, config, "simulation")
            / f"fixed_distribution_welfare_decomposition_{specification}.csv", index=False
        )
    aggregate = pd.concat(rows, ignore_index=True)
    aggregate.to_csv(output_dir(project_root, config, "simulation") / "aggregate_changes.csv", index=False)
    with (output_dir(project_root, config, "simulation") / "counterfactual_results.pkl").open("wb") as stream:
        pickle.dump({"aggregate": aggregate, "solutions": solved, "fixed": fixed_cf}, stream)
    return aggregate


if __name__ == "__main__":
    print(run(Path(__file__).resolve().parents[3]).to_string(index=False))
