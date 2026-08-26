"""Write local outcomes and aggregate appraisal measures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..io.project_io import output_dir
from ..types import EquilibriumResult, ModelData, Parameters


def percent_change(counterfactual: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    return np.divide(100 * (counterfactual - baseline), baseline,
                     out=np.full_like(counterfactual, np.nan, dtype=float), where=baseline != 0)


def write_closure_results(project_root: Path, data: ModelData, baseline: EquilibriumResult,
                          counterfactual: EquilibriumResult, travel_time_baseline: np.ndarray,
                          travel_time_counterfactual: np.ndarray, config: dict,
                          param: Parameters, specification: str = "with_spillovers") -> pd.DataFrame:
    e0, e1 = baseline.endog, counterfactual.endog
    pct = percent_change(e1, e0)
    floor0 = baseline.fundamentals.density * data.land_area ** param.construction_land_share
    floor1 = counterfactual.fundamentals.density * data.land_area ** param.construction_land_share
    revenue0 = e0[:, 5] * e0[:, 2] * floor0 + e0[:, 4] * (1 - e0[:, 2]) * floor0
    revenue1 = e1[:, 5] * e1[:, 2] * floor1 + e1[:, 4] * (1 - e1[:, 2]) * floor1
    land_rent0 = param.construction_land_share * revenue0
    land_rent1 = param.construction_land_share * revenue1
    local = pd.DataFrame({
        "location_id": data.ids,
        "employment_baseline": e0[:, 6], "employment_counterfactual": e1[:, 6], "employment_pct": pct[:, 6],
        "population_baseline": e0[:, 7], "population_counterfactual": e1[:, 7], "population_pct": pct[:, 7],
        "wage_baseline": e0[:, 0], "wage_counterfactual": e1[:, 0], "wage_pct": pct[:, 0],
        "rent_residential_baseline": e0[:, 4], "rent_residential_counterfactual": e1[:, 4], "rent_residential_pct": pct[:, 4],
        "rent_commercial_baseline": e0[:, 5], "rent_commercial_counterfactual": e1[:, 5], "rent_commercial_pct": pct[:, 5],
        "output_baseline": e0[:, 3], "output_counterfactual": e1[:, 3], "output_pct": pct[:, 3],
        "annual_land_rent_baseline": land_rent0, "annual_land_rent_counterfactual": land_rent1,
        "annual_land_rent_pct": percent_change(land_rent1, land_rent0),
    })
    suffix = "" if specification == "with_spillovers" else f"_{specification}"
    local.to_csv(
        output_dir(project_root, config, "simulation")
        / f"block_outcomes_{counterfactual.closure}_city{suffix}.csv",
        index=False,
    )
    mean0 = float(np.sum(baseline.commuting_probability * travel_time_baseline))
    mean1 = float(np.sum(counterfactual.commuting_probability * travel_time_counterfactual))
    baseline_flow_cf = float(np.sum(baseline.commuting_probability * travel_time_counterfactual))
    aggregate = pd.DataFrame([{
        "Specification": specification,
        "Closure": counterfactual.closure,
        "ExpectedUtilityPct": 100 * (counterfactual.utility / baseline.utility - 1),
        "PopulationPct": 100 * (counterfactual.population / baseline.population - 1),
        "GDPPct": 100 * (e1[:, 3].sum() / e0[:, 3].sum() - 1),
        "TotalLandRentPct": 100 * (land_rent1.sum() / land_rent0.sum() - 1),
        "ImmediateCommuteTimeChangePct": 100 * (baseline_flow_cf / mean0 - 1),
        "PostRelocationCommuteTimeChangePct": 100 * (mean1 / mean0 - 1),
        "TotalCommuterMinutesChangePct": 100 * (counterfactual.population * mean1 / (baseline.population * mean0) - 1),
        "Converged": counterfactual.converged,
        "Iterations": counterfactual.iterations,
    }])
    return aggregate
