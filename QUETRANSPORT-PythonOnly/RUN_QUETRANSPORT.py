"""User-facing entry point for the Python-only QUETRANSPORT workflow."""

from __future__ import annotations

import importlib.util
import runpy
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
PIPELINE_FILE = PROJECT_ROOT / "src" / "python" / "run_pipeline.py"
REQUIRED_IMPORTS = {
    "numpy": "numpy", "pandas": "pandas", "PyYAML": "yaml",
    "geopandas": "geopandas", "pyogrio": "pyogrio", "shapely": "shapely",
    "matplotlib": "matplotlib", "scipy": "scipy", "networkx": "networkx", "tqdm": "tqdm",
}


def ensure_environment() -> None:
    missing = [package for package, module in REQUIRED_IMPORTS.items() if importlib.util.find_spec(module) is None]
    if missing:
        print("Installing missing packages: " + ", ".join(missing))
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)], check=True)


def main() -> None:
    ensure_environment()
    runpy.run_path(str(PIPELINE_FILE), run_name="__main__")


if __name__ == "__main__":
    main()
