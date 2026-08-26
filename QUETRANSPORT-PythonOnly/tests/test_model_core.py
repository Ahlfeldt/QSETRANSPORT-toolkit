from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from functions.equilibrium import apply_shocks, solve_closure, solve_fixed_distribution
from functions.inversion import invert_baseline
from functions.types import ModelData, Parameters


def parameters() -> Parameters:
    return Parameters(0.8, 0.75, 0.01, 4.0, 0.0, 0.2, 0.0, 0.3, 0.25, 1e-7, 2000, 0.2, 500)


def data() -> ModelData:
    table = pd.DataFrame({
        "location_id": ["a", "b"], "population": [60.0, 40.0],
        "employment_model": [50.0, 50.0], "rent_floor_space": [1.0, 1.2],
        "land_area": [1.0, 1.0],
    })
    return ModelData(table, table.location_id.to_numpy(), table.population.to_numpy(),
                     table.employment_model.to_numpy(), table.rent_floor_space.to_numpy(),
                     table.land_area.to_numpy())


def test_inversion_matches_observed_marginals():
    d = data()
    inversion = invert_baseline(d, np.array([[1.0, 2.0], [2.0, 1.0]]), parameters())
    assert inversion.converged
    np.testing.assert_allclose(inversion.commuting_probability.sum(1) * 100, d.population, atol=1e-6)
    np.testing.assert_allclose(inversion.commuting_probability.sum(0) * 100, d.employment, atol=1e-6)


def test_closed_city_and_fixed_distribution_run():
    d, p = data(), parameters()
    t0 = np.array([[1.0, 2.0], [2.0, 1.0]])
    inversion = invert_baseline(d, t0, p)
    baseline = solve_closure("closed", p, inversion.fundamentals, t0)
    assert baseline.converged
    assert np.isclose(baseline.population, 100.0)
    fixed = solve_fixed_distribution(p, inversion.fundamentals, t0, t0 * 0.9, baseline, d)
    assert fixed.converged
    assert fixed.welfare_components is not None


def test_open_city_runs_with_nonzero_spillovers():
    d = data()
    p = Parameters(0.8, 0.75, 0.01, 4.0, 0.071, 0.2, 0.155, 0.3, 0.25, 1e-6, 3000, 0.2, 1000)
    travel = np.array([[1.0, 2.0], [2.0, 1.0]])
    inversion = invert_baseline(d, travel, p)
    result = solve_closure("open", p, inversion.fundamentals, travel, inversion.reservation_utility)
    assert result.converged
    assert result.population > 0


def test_standardized_primitive_changes_are_applied():
    d, p = data(), parameters()
    inversion = invert_baseline(d, np.array([[1.0, 2.0], [2.0, 1.0]]), p)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        shock_dir = root / "input" / "standardized" / "shocks"
        shock_dir.mkdir(parents=True)
        pd.DataFrame({
            "location_id": ["a", "b"],
            "productivity_hat": [1.2, 1.0],
            "amenity_hat": [1.0, 1.0],
            "structural_density_hat": [1.0, 1.0],
        }).to_csv(shock_dir / "shocks.csv", index=False)

        shocked = apply_shocks(root, d, inversion.fundamentals, {})

    np.testing.assert_allclose(
        shocked.productivity,
        inversion.fundamentals.productivity * np.array([1.2, 1.0]),
    )
    np.testing.assert_array_equal(shocked.amenity, inversion.fundamentals.amenity)
    np.testing.assert_array_equal(shocked.density, inversion.fundamentals.density)
    assert shocked is not inversion.fundamentals


def test_equilibrium_progress_label_is_printed(capsys):
    d, p = data(), parameters()
    travel = np.array([[1.0, 2.0], [2.0, 1.0]])
    inversion = invert_baseline(d, travel, p)
    solve_closure(
        "closed", p, inversion.fundamentals, travel,
        progress_label="[Main | Counterfactual | Closed city]",
    )
    assert "[Main | Counterfactual | Closed city] iteration 1" in capsys.readouterr().out
