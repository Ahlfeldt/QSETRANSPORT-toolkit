"""Baseline inversion using a stabilized origin-destination balancing routine.

The routine recovers amenity and wage indices that exactly reproduce observed
residential and workplace marginals, then backs out production, construction,
productivity, and amenity primitives using the ARSW equilibrium conditions.
"""

from __future__ import annotations

from math import gamma

import numpy as np

from ..types import Fundamentals, InversionResult, ModelData, Parameters


TINY = np.finfo(float).tiny


def _sinkhorn(kernel: np.ndarray, rows: np.ndarray, cols: np.ndarray,
              tolerance: float, maximum_iterations: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Balance a strictly positive OD kernel to requested probability marginals."""
    u = np.ones_like(rows)
    v = np.ones_like(cols)
    for iteration in range(1, maximum_iterations + 1):
        u = np.divide(rows, kernel @ v, out=np.zeros_like(rows), where=(kernel @ v) > 0)
        v = np.divide(cols, kernel.T @ u, out=np.zeros_like(cols), where=(kernel.T @ u) > 0)
        if iteration % 10 == 0:
            probability = (u[:, None] * kernel) * v[None, :]
            gap = max(np.max(np.abs(probability.sum(1) - rows)), np.max(np.abs(probability.sum(0) - cols)))
            if gap < tolerance:
                return probability, u, v, iteration
    probability = (u[:, None] * kernel) * v[None, :]
    return probability, u, v, maximum_iterations


def invert_baseline(data: ModelData, travel_time: np.ndarray, param: Parameters) -> InversionResult:
    hh = float(data.population.sum())
    residence_share = data.population / hh
    workplace_share = data.employment / hh
    active_residence = residence_share > 0
    active_workplace = workplace_share > 0

    kernel = np.exp(-param.epsilon * param.kappa * travel_time)
    kernel[~active_residence, :] = 0
    kernel[:, ~active_workplace] = 0
    probability, origin_multiplier, destination_multiplier, iterations = _sinkhorn(
        kernel, residence_share, workplace_share, max(param.tolerance, 1e-12), param.maximum_iterations
    )

    # In the commuting equation origin_multiplier = B^eps Q^(-(1-beta)eps)
    # and destination_multiplier = w^eps, up to an irrelevant common scale.
    wage = np.zeros(data.n)
    wage[active_workplace] = np.maximum(destination_multiplier[active_workplace], TINY) ** (1 / param.epsilon)
    wage /= np.average(wage[active_workplace], weights=data.employment[active_workplace])
    amenity_total = np.zeros(data.n)
    amenity_total[active_residence] = (
        np.maximum(origin_multiplier[active_residence], TINY) ** (1 / param.epsilon)
        * data.rent[active_residence] ** (1 - param.beta)
    )
    amenity_total[active_residence] /= np.average(
        amenity_total[active_residence], weights=data.population[active_residence]
    )

    conditional_wage = probability @ wage
    income = hh * conditional_wage
    output = np.zeros(data.n)
    output[active_workplace] = wage[active_workplace] * data.employment[active_workplace] / param.alpha
    commercial_floor = np.zeros(data.n)
    commercial_floor[active_workplace] = (
        (1 - param.alpha) * output[active_workplace] / data.rent[active_workplace]
    )
    residential_floor = np.zeros(data.n)
    residential_floor[active_residence] = (
        (1 - param.beta) * income[active_residence] / data.rent[active_residence]
    )
    total_floor = commercial_floor + residential_floor
    density = np.divide(
        total_floor, data.land_area ** param.construction_land_share,
        out=np.zeros_like(total_floor), where=data.land_area > 0,
    )
    commercial_share = np.divide(commercial_floor, total_floor, out=np.zeros_like(total_floor), where=total_floor > 0)

    productivity_total = np.zeros(data.n)
    productivity_total[active_workplace] = output[active_workplace] / (
        data.employment[active_workplace] ** param.alpha
        * np.maximum(commercial_floor[active_workplace], TINY) ** (1 - param.alpha)
    )
    productivity_density = np.exp(-param.productivity_decay * travel_time) @ np.divide(
        data.employment, data.land_area, out=np.zeros(data.n), where=data.land_area > 0
    )
    amenity_density = np.exp(-param.amenity_decay * travel_time) @ np.divide(
        data.population, data.land_area, out=np.zeros(data.n), where=data.land_area > 0
    )
    productivity_fundamental = np.divide(
        productivity_total,
        np.maximum(productivity_density, TINY) ** param.productivity_spillover,
        out=np.zeros(data.n), where=active_workplace,
    )
    amenity_fundamental = np.divide(
        amenity_total,
        np.maximum(amenity_density, TINY) ** param.amenity_spillover,
        out=np.zeros(data.n), where=active_residence,
    )
    fundamentals = Fundamentals(
        productivity_fundamental, amenity_fundamental, density, data.land_area.copy(),
        data.rent.copy(), data.rent.copy(), data.employment.copy(), data.population.copy(),
        wage.copy(), income.copy(), commercial_share.copy(),
    )
    phi = np.sum(
        kernel * amenity_total[:, None] ** param.epsilon
        * data.rent[:, None] ** (-(1 - param.beta) * param.epsilon)
        * wage[None, :] ** param.epsilon
    )
    utility = gamma((param.epsilon - 1) / param.epsilon) * phi ** (1 / param.epsilon)
    endog = np.column_stack([
        wage, income, commercial_share, output, data.rent, data.rent,
        data.employment, data.population, data.rent, productivity_total,
        amenity_total, productivity_fundamental, amenity_fundamental,
    ])
    row_gap = float(np.max(np.abs(probability.sum(1) - residence_share)))
    col_gap = float(np.max(np.abs(probability.sum(0) - workplace_share)))
    return InversionResult(
        fundamentals, productivity_total, amenity_total, wage, income, commercial_share,
        probability, utility, endog, max(row_gap, col_gap) < max(param.tolerance, 1e-10), iterations,
        {"residence_share_gap": row_gap, "workplace_share_gap": col_gap},
    )
