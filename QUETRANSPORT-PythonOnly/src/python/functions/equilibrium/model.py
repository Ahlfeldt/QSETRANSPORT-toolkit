"""Closed-city, open-city, and fixed-distribution ARSW counterfactuals."""

from __future__ import annotations

from math import gamma
from pathlib import Path

import numpy as np
import pandas as pd

from ..types import EquilibriumResult, Fundamentals, ModelData, Parameters


TINY = np.finfo(float).tiny


def _max_log_gap(old: np.ndarray, new: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        old, new = old[mask], new[mask]
    if old.size == 0:
        return 0.0
    return float(np.max(np.abs(np.log(np.maximum(old, TINY)) - np.log(np.maximum(new, TINY)))))


def apply_shocks(project_root: Path, data: ModelData, fundamentals: Fundamentals,
                 config: dict) -> Fundamentals:
    result = fundamentals.copy()
    shock_file = project_root / "input" / "standardized" / "scenario" / "primitive_hats.csv"
    if not shock_file.exists():
        return result
    shocks = pd.read_csv(shock_file, dtype={"location_id": str}).set_index("location_id")
    aligned = shocks.reindex(data.ids)
    mapping = {
        "productivity_hat": "productivity",
        "amenity_hat": "amenity",
        "structural_density_hat": "density",
    }
    for column, attribute in mapping.items():
        if column in aligned:
            hat = aligned[column].fillna(1.0).to_numpy(float)
            if np.any(hat <= 0):
                raise ValueError(f"{column} must be strictly positive")
            setattr(result, attribute, getattr(result, attribute) * hat)
    return result


def solve_closure(closure: str, param: Parameters, fundamentals: Fundamentals,
                  travel_time: np.ndarray, reservation_utility: float | None = None) -> EquilibriumResult:
    closure = closure.lower()
    if closure not in {"closed", "open"}:
        raise ValueError("closure must be 'closed' or 'open'")
    if closure == "open" and reservation_utility is None:
        raise ValueError("open-city solution requires reservation_utility")

    n = len(fundamentals.land_area)
    a, b = fundamentals.productivity, fundamentals.amenity
    active_work = a > 0
    active_res = b > 0
    mixed = active_work & active_res
    commercial_only = active_work & ~active_res
    residential_only = active_res & ~active_work
    floor_space = fundamentals.density * fundamentals.land_area ** param.construction_land_share
    wage = np.maximum(fundamentals.wage_start.copy(), TINY)
    q_res = np.maximum(fundamentals.rent_residential_start.copy(), TINY)
    q_com = np.maximum(fundamentals.rent_commercial_start.copy(), TINY)
    theta = np.clip(fundamentals.commercial_share_start.copy(), 0, 1)
    hh = float(fundamentals.population_start.sum())
    travel_kernel = np.exp(-param.epsilon * param.kappa * travel_time)
    prod_kernel = np.exp(-param.productivity_decay * travel_time)
    amen_kernel = np.exp(-param.amenity_decay * travel_time)
    path: list[float] = []

    for iteration in range(1, param.maximum_iterations + 1):
        total_amenity = np.zeros(n)
        # Lagged residential distribution is used for the first pass.
        if iteration == 1:
            hr = fundamentals.population_start.copy()
            hm = fundamentals.employment_start.copy()
        prod_density = prod_kernel @ np.divide(hm, fundamentals.land_area, out=np.zeros(n), where=fundamentals.land_area > 0)
        amen_density = amen_kernel @ np.divide(hr, fundamentals.land_area, out=np.zeros(n), where=fundamentals.land_area > 0)
        total_productivity = a * np.maximum(prod_density, TINY) ** param.productivity_spillover
        total_amenity = b * np.maximum(amen_density, TINY) ** param.amenity_spillover

        phi = travel_kernel * (
            total_amenity[:, None] ** param.epsilon
            * q_res[:, None] ** (-(1 - param.beta) * param.epsilon)
            * wage[None, :] ** param.epsilon
        )
        phi[~active_res, :] = 0
        phi[:, ~active_work] = 0
        phi_sum = float(phi.sum())
        if not np.isfinite(phi_sum) or phi_sum <= 0:
            raise RuntimeError("Commuting probabilities are undefined")
        probability = phi / phi_sum
        hr = probability.sum(axis=1) * hh
        hm = probability.sum(axis=0) * hh
        conditional_income = hh * (probability @ wage)

        output = np.zeros(n)
        output[active_work] = (
            total_productivity[active_work]
            * np.maximum(hm[active_work], TINY) ** param.alpha
            * np.maximum(theta[active_work] * floor_space[active_work], TINY) ** (1 - param.alpha)
        )
        wage_new = wage.copy()
        wage_new[active_work] = param.alpha * output[active_work] / np.maximum(hm[active_work], TINY)
        q_res_new, q_com_new = q_res.copy(), q_com.copy()
        q_com_new[commercial_only] = (1 - param.alpha) * output[commercial_only] / np.maximum(
            theta[commercial_only] * floor_space[commercial_only], TINY
        )
        q_res_new[residential_only] = (1 - param.beta) * conditional_income[residential_only] / np.maximum(
            (1 - theta[residential_only]) * floor_space[residential_only], TINY
        )
        mixed_rent = (
            (1 - param.alpha) * output[mixed] + (1 - param.beta) * conditional_income[mixed]
        ) / np.maximum(floor_space[mixed], TINY)
        q_res_new[mixed] = mixed_rent
        q_com_new[mixed] = mixed_rent
        theta_new = theta.copy()
        theta_new[mixed] = np.clip(
            (1 - param.alpha) * output[mixed] / np.maximum(mixed_rent * floor_space[mixed], TINY), 0, 1
        )
        utility = gamma((param.epsilon - 1) / param.epsilon) * phi_sum ** (1 / param.epsilon)
        utility_gap = 0.0 if closure == "closed" else abs(np.log(utility / float(reservation_utility)))
        gap = max(
            _max_log_gap(wage, wage_new, active_work),
            _max_log_gap(q_res, q_res_new, active_res),
            _max_log_gap(q_com, q_com_new, active_work),
            _max_log_gap(theta + 1e-12, theta_new + 1e-12),
            utility_gap,
        )
        path.append(gap)
        if iteration == 1 or iteration % param.print_every == 0:
            print(f"{closure.capitalize()} equilibrium iteration {iteration}: max log gap={gap:.3e}")
        if gap < param.tolerance:
            wage, q_res, q_com, theta = wage_new, q_res_new, q_com_new, theta_new
            break
        weight = np.clip(param.damping, 0.01, 0.95)
        wage = (1 - weight) * wage + weight * wage_new
        q_res = (1 - weight) * q_res + weight * q_res_new
        q_com = (1 - weight) * q_com + weight * q_com_new
        theta = (1 - weight) * theta + weight * theta_new
        if closure == "open":
            hh_target = hh * (utility / float(reservation_utility)) ** param.epsilon
            hh = 0.95 * hh + 0.05 * hh_target
    else:
        iteration = param.maximum_iterations

    converged = path[-1] < param.tolerance
    # Recompute final accounting columns from the last evaluated state.
    combined_rent = np.where(active_res, q_res, q_com)
    endog = np.column_stack([
        wage, conditional_income, theta, output, q_res, q_com, hm, hr,
        combined_rent, total_productivity, total_amenity, a, b,
    ])
    return EquilibriumResult(
        closure, endog, fundamentals, probability, hh, utility, converged,
        iteration, path,
    )


def solve_fixed_distribution(param: Parameters, fundamentals: Fundamentals,
                             travel_time_baseline: np.ndarray, travel_time_counterfactual: np.ndarray,
                             baseline: EquilibriumResult, data: ModelData) -> EquilibriumResult:
    e0 = baseline.endog
    e1 = e0.copy()
    employment, population = e0[:, 6], e0[:, 7]
    theta = e0[:, 2]
    prod_density = np.exp(-param.productivity_decay * travel_time_counterfactual) @ (employment / data.land_area)
    amen_density = np.exp(-param.amenity_decay * travel_time_counterfactual) @ (population / data.land_area)
    productivity = fundamentals.productivity * np.maximum(prod_density, TINY) ** param.productivity_spillover
    amenity = fundamentals.amenity * np.maximum(amen_density, TINY) ** param.amenity_spillover
    floor_space = fundamentals.density * data.land_area ** param.construction_land_share
    commercial_floor = theta * floor_space
    output = np.zeros(data.n)
    active = employment > 0
    output[active] = productivity[active] * employment[active] ** param.alpha * np.maximum(
        commercial_floor[active], TINY
    ) ** (1 - param.alpha)
    wage = np.zeros(data.n)
    wage[active] = param.alpha * output[active] / employment[active]
    income = baseline.population * (baseline.commuting_probability @ wage)
    e1[:, 0], e1[:, 1], e1[:, 3], e1[:, 9], e1[:, 10] = wage, income, output, productivity, amenity
    p = baseline.commuting_probability
    amenity_component = float(np.sum(p.sum(1) * np.log(np.maximum(amenity, TINY) / np.maximum(e0[:, 10], TINY))))
    wage_component = float(np.sum(p.sum(0) * np.log(np.maximum(wage, TINY) / np.maximum(e0[:, 0], TINY))))
    commute_component = float(-param.kappa * np.sum(p * (travel_time_counterfactual - travel_time_baseline)))
    total = amenity_component + wage_component + commute_component
    components = {
        "commuting_log_change": commute_component,
        "productivity_wage_log_change": wage_component,
        "amenity_log_change": amenity_component,
        "total_log_change": total,
        "commuting_pct": 100 * np.expm1(commute_component),
        "productivity_wage_pct": 100 * np.expm1(wage_component),
        "amenity_pct": 100 * np.expm1(amenity_component),
        "total_pct": 100 * np.expm1(total),
    }
    return EquilibriumResult(
        "fixed_distribution", e1, fundamentals, p.copy(), baseline.population,
        baseline.utility * np.exp(total), True, 0, [], components,
    )
