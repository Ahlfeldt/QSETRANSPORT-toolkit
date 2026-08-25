"""Complete GRID → TTMATRIX → Python model → maps workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PYTHON_SOURCE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PYTHON_SOURCE_DIR.parent.parent
sys.path.insert(0, str(PYTHON_SOURCE_DIR))

from common.config import load_config, save_runtime_config
from common.scenario import prepare_primitive_shocks
from grid.generate_grid_inputs import generate_grid_inputs
from grid.prepare_grid_inputs import prepare_grid_inputs
from reporting.make_maps import make_maps
from reporting.make_shock_maps import make_shock_maps
from scripts.run_all import run as run_model
from ttmatrix.generate_travel_times import generate_travel_times
from ttmatrix.prepare_travel_times import prepare_travel_times


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Python-only QUETRANSPORT.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "project_config.yaml"))
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--skip-maps", action="store_true")
    args = parser.parse_args()
    config, project_root = load_config(args.config)
    print("=" * 72)
    print(f"QUETRANSPORT Python-only: {config['project']['name']}")
    print(f"Project directory:       {project_root}")
    print("=" * 72)

    reuse_inputs = bool(config["project"].get("reuse_standardized_inputs", False))
    if reuse_inputs:
        print("\n[1-3/5] INPUT PREPARATION SKIPPED")
        print("        Using the self-contained copied standardized inputs unchanged.")
    elif not args.model_only:
        if config["project"]["run_grid"]:
            print("\n[1/5] GRID")
            if config["grid"].get("mode") == "generate_from_source_layers":
                generate_grid_inputs(config)
            else:
                prepare_grid_inputs(config)
        if config["project"]["run_ttmatrix"]:
            print("\n[2/5] TTMATRIX")
            if config["ttmatrix"]["source"] == "ttmatrix":
                generate_travel_times(config)
            else:
                prepare_travel_times(config)
        print("\n[3/5] SCENARIO INTERFACE")
        scenario_report = prepare_primitive_shocks(config)
        if scenario_report["active"] and config["reporting"].get("make_maps", True):
            make_shock_maps(config, scenario_report)
        save_runtime_config(config, Path(config["paths"]["standardized_input"]) / "runtime_config.json")
    if args.prepare_only:
        return 0

    print("\n[4/5] PYTHON ECONOMIC MODEL")
    run_model(project_root)
    if config["reporting"].get("make_maps", True) and not args.skip_maps:
        print("\n[5/5] MAPS")
        make_maps(args.config)
    print("\nQUETRANSPORT Python-only completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
