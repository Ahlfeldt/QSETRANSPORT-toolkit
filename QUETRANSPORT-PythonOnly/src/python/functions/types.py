"""Typed data containers shared by scripts and model functions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Parameters:
    alpha: float
    beta: float
    kappa: float
    epsilon: float
    productivity_spillover: float
    productivity_decay: float
    amenity_spillover: float
    amenity_decay: float
    construction_land_share: float
    tolerance: float
    maximum_iterations: int
    damping: float
    print_every: int

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Parameters":
        model, numerics = config["model"], config["numerics"]
        value = cls(
            alpha=float(model["production_share_labor"]),
            beta=float(model["expenditure_share_consumption"]),
            kappa=float(model["commuting_time_coefficient"]),
            epsilon=float(model["commuting_elasticity"]),
            productivity_spillover=float(model["productivity_spillover"]),
            productivity_decay=float(model["productivity_spatial_decay"]),
            amenity_spillover=float(model["amenity_spillover"]),
            amenity_decay=float(model["amenity_spatial_decay"]),
            construction_land_share=float(model["construction_land_share"]),
            tolerance=float(numerics["tolerance_equilibrium"]),
            maximum_iterations=min(int(numerics["maximum_iterations"]), 10_000),
            damping=float(numerics["damping_equilibrium"]),
            print_every=int(numerics["print_every"]),
        )
        if not 0 < value.alpha < 1 or not 0 < value.beta < 1:
            raise ValueError("Production and consumption shares must lie in (0, 1).")
        return value


@dataclass
class ModelData:
    table: pd.DataFrame
    ids: np.ndarray
    population: np.ndarray
    employment: np.ndarray
    rent: np.ndarray
    land_area: np.ndarray

    @property
    def n(self) -> int:
        return len(self.ids)


@dataclass
class Fundamentals:
    productivity: np.ndarray
    amenity: np.ndarray
    density: np.ndarray
    land_area: np.ndarray
    rent_residential_start: np.ndarray
    rent_commercial_start: np.ndarray
    employment_start: np.ndarray
    population_start: np.ndarray
    wage_start: np.ndarray
    income_start: np.ndarray
    commercial_share_start: np.ndarray

    def copy(self) -> "Fundamentals":
        return Fundamentals(**{name: value.copy() for name, value in vars(self).items()})


@dataclass
class EquilibriumResult:
    closure: str
    endog: np.ndarray
    fundamentals: Fundamentals
    commuting_probability: np.ndarray
    population: float
    utility: float
    converged: bool
    iterations: int
    convergence_path: list[float] = field(default_factory=list)
    welfare_components: dict[str, float] | None = None


@dataclass
class InversionResult:
    fundamentals: Fundamentals
    total_productivity: np.ndarray
    total_amenity: np.ndarray
    wage: np.ndarray
    income: np.ndarray
    commercial_share: np.ndarray
    commuting_probability: np.ndarray
    reservation_utility: float
    endog: np.ndarray
    converged: bool
    iterations: int
    diagnostics: dict[str, float]
