"""QUETRANSPORT MASTER PIPELINE.

This is the only Python file a normal user needs to run. It can be run:

1. directly from Spyder by pressing Run; or
2. from PowerShell with ``python src/python/run_pipeline.py``.

All substantive choices are read from ``project_config.yaml``. The
user should edit that YAML file rather than changing settings in this code.
"""
from __future__ import annotations

# =========================================================================
# 0. IMPORT STANDARD PYTHON TOOLS
# =========================================================================
# argparse lets an advanced user select a different configuration file.
# subprocess lets Python open a separate MATLAB session for the model stage.
# sys and pathlib provide portable paths and clear error handling.
import argparse
import subprocess
import sys
from pathlib import Path


# =========================================================================
# 1. LOCATE QUETRANSPORT AND ITS DEFAULT CONFIGURATION
# =========================================================================
# This script lives in QUETRANSPORT/src/python. We derive every path from
# that location, so the workflow does not depend on Spyder's working folder.
PYTHON_SOURCE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PYTHON_SOURCE_DIR.parent.parent
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "project_config.yaml"

# Add the Python source folder so the small functions in common, grid,
# ttmatrix, and reporting can be imported from their separate folders.
sys.path.insert(0, str(PYTHON_SOURCE_DIR))

# Configuration tools: read the one YAML file, check choices, and create the
# JSON snapshot that MATLAB can read with its standard jsondecode command.
from common.config import ConfigurationError, load_config, save_runtime_config
from common.scenario import ScenarioInputError, prepare_primitive_shocks

# GRID tools: either generate the analysis grid from raw polygon layers or,
# in optional compatibility mode, standardize a precomputed GRID output.
from grid.generate_grid_inputs import generate_grid_inputs
from grid.prepare_grid_inputs import GridInputError, prepare_grid_inputs

# TTMATRIX tools: either generate the no-network and network matrices or,
# in optional compatibility mode, validate two existing matrices.
from ttmatrix.generate_travel_times import generate_travel_times
from ttmatrix.prepare_travel_times import MatrixInputError, prepare_travel_times

# Reporting tool: join MATLAB results to the standardized geometry and map
# relative changes after the model has finished.
from reporting.make_maps import make_maps
from reporting.make_shock_maps import ShockMapError, make_shock_maps


def run_matlab(project_root: Path, matlab_command: str) -> None:
    """Open a new MATLAB process and run inversion plus counterfactuals."""
    # run_all.m first calls invert_baseline.m and then run_counterfactual.m.
    master_script = project_root / "src" / "matlab" / "scripts" / "run_all.m"
    if not master_script.is_file():
        raise FileNotFoundError(f"MATLAB master script not found: {master_script}")

    # MATLAB accepts forward slashes on Windows. Replacing them avoids a
    # backslash being interpreted as an escape character in the batch text.
    matlab_path = master_script.as_posix().replace("'", "''")
    batch_instruction = f"run('{matlab_path}')"

    print("\n[4/5] Starting a separate MATLAB session.")
    print("      MATLAB will invert the baseline and solve the requested city closures.")
    # Read MATLAB's combined output stream line by line and immediately echo
    # it to Python. This makes MATLAB progress, convergence messages, warnings,
    # and errors visible live in both the Spyder console and PowerShell.
    process = subprocess.Popen(
        [matlab_command, "-batch", batch_instruction],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    for matlab_line in process.stdout:
        # MATLAB emits many blank lines around unsuppressed legacy output.
        # Dropping empty records keeps the progress indicators readable.
        if not matlab_line.strip():
            continue
        print(f"[MATLAB] {matlab_line}", end="", flush=True)
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, process.args)
    print("      MATLAB inversion and simulations completed successfully.")


def main() -> int:
    """Execute the cumulative GRID → TTMATRIX → MATLAB → maps workflow."""
    # ---------------------------------------------------------------------
    # COMMAND-LINE OPTIONS
    # ---------------------------------------------------------------------
    # --config is optional. With no arguments—as in a normal Spyder run—the
    # script automatically uses project_config.yaml.
    # --prepare-only is useful when inputs should be generated on one machine
    # and the MATLAB stage will later be run manually on a server.
    parser = argparse.ArgumentParser(description="Run the complete QUETRANSPORT workflow.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_FILE),
        help="YAML configuration file (default: project_config.yaml)",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Generate and validate MATLAB inputs, but do not start MATLAB or maps.",
    )
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="Run preparation and MATLAB, but do not regenerate maps.",
    )
    args = parser.parse_args()

    try:
        # =================================================================
        # 2. READ AND VALIDATE THE USER'S SINGLE CONFIGURATION FILE
        # =================================================================
        config, project_root = load_config(args.config)
        print("=" * 72)
        print(f"QUETRANSPORT project: {config['project']['name']}")
        print(f"Project directory:    {project_root}")
        print(f"Configuration file:   {Path(args.config).resolve()}")
        print("=" * 72)

        # =================================================================
        # 3. GRID STAGE: CREATE FINAL MODEL BLOCKS AND MODEL VARIABLES
        # =================================================================
        if config["project"]["run_grid"]:
            print("\n[1/5] GRID: creating standardized blocks and geography.")
            if config["grid"].get("mode") == "generate_from_source_layers":
                grid_report = generate_grid_inputs(config)
            else:
                grid_report = prepare_grid_inputs(config)
            print(f"      Retained model locations: {grid_report['number_of_locations']}")
            print("      Created locations.csv, polygon geography, and centroids.")
        else:
            print("\n[1/5] GRID stage skipped by project_config.yaml.")

        # =================================================================
        # 4. TTMATRIX STAGE: CREATE BASELINE AND POLICY TRAVEL TIMES
        # =================================================================
        if config["project"]["run_ttmatrix"]:
            print("\n[2/5] TTMATRIX: creating and validating both travel matrices.")
            if config["ttmatrix"]["source"] == "ttmatrix":
                print("      Source: TTMATRIX construction from centroids and network files.")
                matrix_report = generate_travel_times(config)
            else:
                print("      Source: user-provided baseline and counterfactual matrices.")
                matrix_report = prepare_travel_times(config)
            print(f"      Improved OD pairs: {matrix_report['improved_pairs']}")
            print(f"      Slower OD pairs:   {matrix_report['slower_pairs']}")
            print("      Created aligned baseline and counterfactual matrices.")
        else:
            print("\n[2/5] TTMATRIX stage skipped by project_config.yaml.")

        # =================================================================
        # 5. PREPARE OPTIONAL NON-TRANSPORT FUNDAMENTAL CHANGES
        # =================================================================
        # The user may combine the transport change with multiplicative changes
        # in productivity, amenity, or structural density. A null polygon path
        # creates no standardized shock, so every fundamental hat equals one.
        scenario_report = prepare_primitive_shocks(config)
        if scenario_report["active"]:
            print("\n[3/5] INTERFACE: area-interpolated optional primitive changes.")
            print(f"      Locations with at least one change: {scenario_report['changed_locations']}")
            print(f"      Source polygons: {scenario_report['source_file']}")
            print(f"      Standardized shocks: {scenario_report['standardized_file']}")
            if config["reporting"].get("make_maps", True):
                shock_maps = make_shock_maps(config, scenario_report)
                print("      Visual cross-check maps:")
                for shock_map in shock_maps:
                    print(f"        {shock_map}")
        else:
            print("\n[3/5] INTERFACE: no non-transport primitive changes requested.")
            print("      Productivity, amenity, and structural-density hats equal one.")

        # Export the fully resolved configuration that MATLAB reads.
        runtime_path = Path(config["paths"]["standardized_input"]) / "runtime_config.json"
        save_runtime_config(config, runtime_path)
        print(f"      Runtime configuration: {runtime_path}")

        # A user working across machines can stop here, copy/sync the project,
        # and run src/matlab/scripts/run_all.m manually on the MATLAB server.
        if args.prepare_only:
            print("\nPreparation-only mode selected. MATLAB and maps were not run.")
            return 0

        # =================================================================
        # 6. MATLAB STAGE: INVERT THE MODEL AND SOLVE COUNTERFACTUALS
        # =================================================================
        run_model = bool(config["project"].get("run_inversion", True) or
                         config["project"].get("run_simulation", True))
        if run_model:
            matlab_command = str(config["project"].get("matlab_command", "matlab"))
            run_matlab(project_root, matlab_command)
        else:
            print("\n[4/5] MATLAB stage skipped by project_config.yaml.")

        # =================================================================
        # 7. REPORTING STAGE: CREATE MAPS FROM MATLAB OUTPUTS
        # =================================================================
        if config["reporting"].get("make_maps", True) and not args.skip_maps:
            print("\n[5/5] REPORTING: mapping relative equilibrium changes.")
            make_maps(args.config)
        else:
            print("\n[5/5] Map generation skipped.")

        print("\n" + "=" * 72)
        print("QUETRANSPORT completed successfully.")
        print(f"Results directory: {config['paths']['output']}")
        print("=" * 72)
        return 0

    except subprocess.CalledProcessError as error:
        print(f"\nQUETRANSPORT stopped because MATLAB failed (exit code {error.returncode}).", file=sys.stderr)
        return 1
    except (ConfigurationError, GridInputError, MatrixInputError, ScenarioInputError,
            ShockMapError, FileNotFoundError, OSError, ValueError) as error:
        print(f"\nQUETRANSPORT stopped: {error}", file=sys.stderr)
        return 1


# This standard Python guard means:
# - Spyder runs main() when the user presses Run;
# - importing this file from another Python program does not start the model.
if __name__ == "__main__":
    raise SystemExit(main())
