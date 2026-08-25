"""Read, validate, resolve, and export the single QUETRANSPORT configuration."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when a user-facing configuration choice is missing or invalid."""


def _deep_update(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge user choices into safe defaults."""
    result = copy.deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


DEFAULTS: dict[str, Any] = {
    "project": {
        "name": "quetransport_project",
        "run_grid": True,
        "run_ttmatrix": True,
        "run_inversion": True,
        "run_simulation": True,
        "run_no_spillover_comparison": True,
    },
    "grid": {
        "geometry_id_variable": None,
        "original_id_variable": None,
        "rent_variable": None,
        "target_crs": None,
        "missing_value_rule": "stop",
    },
    "ttmatrix": {
        "source": "ttmatrix",
        "time_unit": "minutes",
        "intrazonal_rule": "keep",
        "intrazonal_minutes": 0.0,
        "unreachable_rule": "stop",
    },
    "model": {
        "city_closure": "both",
        "productivity_spillover": 0.0,
        "amenity_spillover": 0.0,
        "construction_capital_share": 0.75,
        "construction_land_share": 0.25,
    },
    "numerics": {
        "maximum_inversion_passes": 10,
        "tolerance_inversion": 1.0e-6,
        "tolerance_equilibrium": 1.0e-6,
        "maximum_iterations": 10000,
        "damping_inversion": 0.10,
        "damping_equilibrium": 0.10,
        "print_every": 25,
        "save_convergence_trace": True,
    },
    "reporting": {"make_maps": False, "save_csv": True, "save_mat": True},
}


def _require(mapping: dict[str, Any], dotted_name: str) -> Any:
    value: Any = mapping
    for part in dotted_name.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ConfigurationError(f"Missing required configuration choice: {dotted_name}")
        value = value[part]
    if value is None or value == "":
        raise ConfigurationError(f"Configuration choice cannot be empty: {dotted_name}")
    return value


def _resolve_path(value: str | None, project_root: Path) -> str | None:
    if value is None or value == "":
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve())


def load_config(config_path: str | Path) -> tuple[dict[str, Any], Path]:
    """Load YAML, apply defaults, validate choices, and resolve all paths."""
    config_path = Path(config_path).expanduser().resolve()
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    # The active configuration sits in the project root beside
    # RUN_QUETRANSPORT.py. Optional templates may still be selected from the
    # config subfolder with --config, so support both locations explicitly.
    if config_path.parent.name.lower() == "config":
        project_root = config_path.parent.parent
    else:
        project_root = config_path.parent
    with config_path.open("r", encoding="utf-8") as stream:
        user = yaml.safe_load(stream) or {}
    if not isinstance(user, dict):
        raise ConfigurationError("The YAML root must be a mapping of named sections.")
    config = _deep_update(DEFAULTS, user)

    for name in ("paths.standardized_input", "paths.output"):
        _require(config, name)
    grid_mode = config["grid"].get("mode", "standardize_existing_output")
    if grid_mode == "generate_from_source_layers":
        for name in ("paths.source_grid_folder",
                     "grid.population_source_variable", "grid.employment_source_variable",
                     "grid.total_population"):
            _require(config, name)
        cell_geometry = str(config["grid"].get("cell_geometry", "square")).lower()
        if cell_geometry not in {"square", "hexagon", "original"}:
            raise ConfigurationError(
                "grid.cell_geometry must be square, hexagon, or original."
            )
        config["grid"]["cell_geometry"] = cell_geometry
        if cell_geometry != "original":
            _require(config, "grid.cell_size_km")
    elif grid_mode == "standardize_existing_output":
        for name in ("paths.source_grid_csv", "paths.source_grid_geometry",
                     "grid.id_variable", "grid.population_variable",
                     "grid.employment_variable", "grid.rent_variable"):
            _require(config, name)
    else:
        raise ConfigurationError("grid.mode must be generate_from_source_layers or standardize_existing_output.")

    # A simple public choice replaces the older internal mode terminology.
    # The fallback keeps older configuration files usable.
    travel_source = config["ttmatrix"].get("source")
    if travel_source is None:
        old_mode = config["ttmatrix"].get("mode", "standardize_existing_matrices")
        travel_source = ("ttmatrix" if old_mode == "generate_from_network"
                         else "user_provided")
    travel_source = str(travel_source).lower()

    if travel_source == "ttmatrix":
        for name in ("paths.counterfactual_network", "paths.counterfactual_stations",
                     "ttmatrix.off_network_speed_kmh", "ttmatrix.network_speed_kmh"):
            _require(config, name)
        baseline_network = config.get("paths", {}).get("baseline_network")
        baseline_stations = config.get("paths", {}).get("baseline_stations")
        if bool(baseline_network) != bool(baseline_stations):
            raise ConfigurationError(
                "Supply both paths.baseline_network and paths.baseline_stations, "
                "or set both to null."
            )
        config["ttmatrix"]["mode"] = "generate_from_network"
    elif travel_source == "user_provided":
        for name in ("paths.baseline_matrix", "paths.counterfactual_matrix"):
            _require(config, name)
        config["ttmatrix"]["mode"] = "standardize_existing_matrices"
    else:
        raise ConfigurationError("ttmatrix.source must be ttmatrix or user_provided.")
    config["ttmatrix"]["source"] = travel_source

    closure = str(config["model"]["city_closure"]).lower()
    if closure not in {"closed", "open", "both"}:
        raise ConfigurationError("model.city_closure must be closed, open, or both.")
    config["model"]["city_closure"] = closure

    if config["ttmatrix"]["time_unit"] not in {"minutes", "seconds", "hours"}:
        raise ConfigurationError("ttmatrix.time_unit must be minutes, seconds, or hours.")
    if config["grid"]["missing_value_rule"] not in {"stop", "drop"}:
        raise ConfigurationError("grid.missing_value_rule must be stop or drop.")

    land = float(config["model"]["construction_land_share"])
    capital = float(config["model"]["construction_capital_share"])
    if abs(land + capital - 1.0) > 1e-10:
        raise ConfigurationError("Construction land and capital shares must sum to one.")

    path_keys = ("source_grid_folder", "source_grid_csv", "source_grid_geometry",
                 "baseline_matrix", "counterfactual_matrix",
                 "baseline_network", "baseline_stations",
                 "counterfactual_network", "counterfactual_stations",
                 "standardized_input", "output")
    paths = config.setdefault("paths", {})
    for key in path_keys:
        if key in paths:
            paths[key] = _resolve_path(paths[key], project_root)

    # Resolve the optional scenario file from its user-facing scenario section.
    scenario = config.setdefault("scenario", {})
    scenario["shocks_shapefile"] = _resolve_path(scenario.get("shocks_shapefile"), project_root)
    config["runtime"] = {
        "project_root": str(project_root),
        "source_config": str(config_path),
    }
    return config, project_root


def save_runtime_config(config: dict[str, Any], destination: str | Path) -> Path:
    """Save the resolved configuration that MATLAB reads with jsondecode."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return destination
