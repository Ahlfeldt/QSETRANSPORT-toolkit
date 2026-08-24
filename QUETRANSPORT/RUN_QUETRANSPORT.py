"""RUN QUETRANSPORT.

THIS IS THE ONLY SCRIPT A NORMAL USER NEEDS TO EXECUTE.

Before running it:
1. copy the raw grid and counterfactual network shapefiles into ``input/raw``;
2. choose all parameters in ``project_config.yaml``.

Then run this file from Spyder, or from PowerShell with:

    python RUN_QUETRANSPORT.py

The script first installs any missing Python packages into the active Python
environment. It then runs the complete GRID → TTMATRIX → MATLAB → maps
workflow defined in ``src/python/run_pipeline.py``.
"""
from __future__ import annotations

# =========================================================================
# 1. LOCATE THE PROJECT FROM THIS ROOT-LEVEL MASTER FILE
# =========================================================================
# Because every path is derived from __file__, Spyder's current working
# directory and PowerShell's current directory do not affect the workflow.
import importlib.util
from pathlib import Path
import runpy
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
PIPELINE_FILE = PROJECT_ROOT / "src" / "python" / "run_pipeline.py"


# =========================================================================
# 2. CHECK THE PYTHON ENVIRONMENT AND INSTALL ONLY MISSING PACKAGES
# =========================================================================
# Package names used by pip do not always equal their Python import names.
# This dictionary makes the test explicit and easy to understand.
REQUIRED_IMPORTS = {
    "numpy": "numpy",
    "pandas": "pandas",
    "PyYAML": "yaml",
    "geopandas": "geopandas",
    "pyogrio": "pyogrio",
    "shapely": "shapely",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "networkx": "networkx",
    "tqdm": "tqdm",
}


def missing_packages() -> list[str]:
    """Return user-facing package names that cannot currently be imported."""
    return [package for package, module in REQUIRED_IMPORTS.items()
            if importlib.util.find_spec(module) is None]


def ensure_environment() -> None:
    """Install requirements only when one or more imports are unavailable."""
    missing = missing_packages()
    if not missing:
        print("[ENVIRONMENT] All required Python packages are available.")
        return

    print("[ENVIRONMENT] Missing packages: " + ", ".join(missing))
    print("[ENVIRONMENT] Installing requirements into this Python environment:")
    print(f"              {sys.executable}")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        check=True,
    )

    # Check again so a failed or incomplete installation produces a clear error.
    still_missing = missing_packages()
    if still_missing:
        raise RuntimeError(
            "Installation finished but these packages remain unavailable: "
            + ", ".join(still_missing)
        )
    print("[ENVIRONMENT] Python environment is ready.")


# =========================================================================
# 3. RUN THE COMPLETE QUETRANSPORT PIPELINE
# =========================================================================
def main() -> None:
    """Prepare the environment and hand control to the documented pipeline."""
    print("=" * 72)
    print("QUETRANSPORT MASTER SCRIPT")
    print(f"Project directory: {PROJECT_ROOT}")
    print("=" * 72)
    ensure_environment()

    if not PIPELINE_FILE.is_file():
        raise FileNotFoundError(f"Pipeline file not found: {PIPELINE_FILE}")

    # runpy executes the maintained pipeline as if the user had run that file
    # directly. PowerShell options such as --prepare-only remain available.
    runpy.run_path(str(PIPELINE_FILE), run_name="__main__")


# Spyder executes this block when the user presses Run. Importing the file
# from another program does not unexpectedly start package installation.
if __name__ == "__main__":
    main()
