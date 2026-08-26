"""Map equilibrium impacts and overlay the counterfactual transport innovation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(THIS_DIR))
from common.config import load_config
from common.identifiers import canonical_series

BASE_OUTCOMES = {
    "employment_pct": "Employment change (%)",
    "population_pct": "Population change (%)",
    "wage_pct": "Wage change (%)",
    "output_pct": "Output change (%)",
}

RESIDENTIAL_PRICE = "rent_residential_pct"
COMMERCIAL_PRICE = "rent_commercial_pct"
COMBINED_PRICE = "floor_space_price_pct"


def symmetric_thresholds(values: pd.Series) -> np.ndarray | None:
    """Return three positive, dispersion-adaptive thresholds around zero."""
    finite = pd.to_numeric(values, errors="coerce")
    valid = finite[np.isfinite(finite)]
    magnitudes = np.abs(valid.to_numpy(dtype=float))
    magnitudes = magnitudes[magnitudes > 1.0e-12]
    if magnitudes.size == 0:
        return None

    thresholds = np.quantile(magnitudes, [0.25, 0.50, 0.75])
    if not np.all(np.diff(thresholds) > 1.0e-12):
        scale = float(np.median(magnitudes))
        thresholds = scale * np.array([0.5, 1.0, 2.0])
    return thresholds


def classified_values(
    values: pd.Series, thresholds: np.ndarray | None
) -> tuple[pd.Series, list[str]]:
    """Classify changes into three negative, one central, and three positive bins."""
    finite = pd.to_numeric(values, errors="coerce")
    if thresholds is None:
        classified = pd.Series(pd.NA, index=values.index, dtype="Int64")
        classified.loc[finite.notna()] = 3
        return classified, ["No change"]

    q1, q2, q3 = thresholds
    classified = pd.Series(pd.NA, index=values.index, dtype="Int64")
    valid = finite.notna() & np.isfinite(finite)
    classified.loc[valid] = 3
    classified.loc[valid & (finite < -q1)] = 2
    classified.loc[valid & (finite <= -q2)] = 1
    classified.loc[valid & (finite <= -q3)] = 0
    classified.loc[valid & (finite > q1)] = 4
    classified.loc[valid & (finite >= q2)] = 5
    classified.loc[valid & (finite >= q3)] = 6
    labels = [
        f"≤ {-q3:.3g}",
        f"{-q3:.3g} to {-q2:.3g}",
        f"{-q2:.3g} to {-q1:.3g}",
        f"{-q1:.3g} to {q1:.3g}",
        f"{q1:.3g} to {q2:.3g}",
        f"{q2:.3g} to {q3:.3g}",
        f"> {q3:.3g}",
    ]
    return classified, labels


def _transport_innovation(config: dict, map_crs) -> gpd.GeoDataFrame | None:
    """Return counterfactual links that are absent from the baseline network.

    If the baseline network paths are null, the entire counterfactual network
    is the innovation. When both networks exist, common links are removed in a
    projected CRS with a small one-metre tolerance for coordinate differences.
    User-provided travel-time matrices need not have network geometry, in which
    case the maps are produced without an overlay.
    """
    if config["ttmatrix"]["source"] != "ttmatrix":
        return None

    counter_path = config["paths"].get("counterfactual_network")
    if not counter_path or not Path(counter_path).is_file():
        return None
    counter = gpd.read_file(counter_path)
    if counter.empty:
        return None
    if counter.crs is None:
        raise ValueError("Counterfactual network has no CRS and cannot be mapped.")

    baseline_path = config["paths"].get("baseline_network")
    if not baseline_path:
        innovation = counter[["geometry"]].copy()
    else:
        baseline_path = Path(baseline_path)
        if not baseline_path.is_file():
            raise FileNotFoundError(f"Configured baseline network not found: {baseline_path}")
        baseline = gpd.read_file(baseline_path)
        if baseline.crs is None:
            raise ValueError("Baseline network has no CRS and cannot be compared.")
        if baseline.empty:
            innovation = counter[["geometry"]].copy()
        else:
            projected_crs = counter.estimate_utm_crs()
            if projected_crs is None:
                raise ValueError("Could not choose a projected CRS for network comparison.")
            counter_projected = counter.to_crs(projected_crs)
            baseline_union = baseline.to_crs(projected_crs).geometry.union_all()
            baseline_buffer = baseline_union.buffer(1.0)
            innovation = counter_projected[["geometry"]].copy()
            innovation["geometry"] = innovation.geometry.map(
                lambda line: line.difference(baseline_buffer)
            )
            innovation = innovation.loc[
                innovation.geometry.notna() & ~innovation.geometry.is_empty
            ]
    if innovation.empty:
        return None
    return innovation.to_crs(map_crs)


def _outcomes_for_results(results: pd.DataFrame) -> tuple[dict[str, str], bool]:
    """Use one price map when residential and commercial impacts coincide."""
    outcomes = dict(BASE_OUTCOMES)
    residential = pd.to_numeric(results[RESIDENTIAL_PRICE], errors="coerce")
    commercial = pd.to_numeric(results[COMMERCIAL_PRICE], errors="coerce")
    valid = residential.notna() & commercial.notna()
    identical = bool(
        valid.any()
        and np.allclose(
            residential[valid],
            commercial[valid],
            rtol=1e-10,
            atol=1e-8,
        )
    )
    if identical:
        results[COMBINED_PRICE] = 0.5 * (residential + commercial)
        outcomes[COMBINED_PRICE] = "Floor-space price change (%)"
    else:
        outcomes[RESIDENTIAL_PRICE] = "Residential floor-space price change (%)"
        outcomes[COMMERCIAL_PRICE] = "Commercial floor-space price change (%)"
    return outcomes, identical


def _remove_redundant_price_maps(map_dir: Path, closure: str) -> None:
    """Remove stale separate price maps after they have become redundant."""
    for variable in (RESIDENTIAL_PRICE, COMMERCIAL_PRICE):
        for extension in ("pdf", "png"):
            path = map_dir / f"{closure}_city_{variable}.{extension}"
            if path.exists():
                path.unlink()


def make_maps(config_path: str | Path) -> None:
    config, root = load_config(config_path)
    geography_path = (
        Path(config["paths"]["standardized_input"]) / "geography" / "locations.gpkg"
    )
    geometry = gpd.read_file(geography_path, layer="locations")
    geometry["location_id"] = canonical_series(geometry["location_id"])
    innovation = _transport_innovation(config, geometry.crs)

    map_dir = Path(config["paths"]["output"]) / "maps"
    map_dir.mkdir(parents=True, exist_ok=True)
    closure_choice = config["model"]["city_closure"]
    closures = ["closed", "open"] if closure_choice == "both" else [closure_choice]

    scenario_maps: dict[str, tuple[gpd.GeoDataFrame, dict[str, str]]] = {}
    pooled_values: dict[str, list[pd.Series]] = {}
    for closure in closures:
        result_path = (
            Path(config["paths"]["output"])
            / "simulation"
            / f"block_outcomes_{closure}_city.csv"
        )
        if not result_path.is_file():
            raise FileNotFoundError(f"Run MATLAB simulation first; missing {result_path}")
        results = pd.read_csv(result_path, dtype={"location_id": "string"})
        results["location_id"] = canonical_series(results["location_id"])
        outcomes, prices_identical = _outcomes_for_results(results)
        if prices_identical:
            _remove_redundant_price_maps(map_dir, closure)
            print(
                f"      {closure.capitalize()} city: residential and commercial "
                "price changes coincide; creating one floor-space-price map."
            )

        mapped = geometry.merge(
            results, on="location_id", how="left", validate="one_to_one"
        )
        if mapped[list(outcomes)].isna().all(axis=None):
            raise ValueError(
                f"No simulation results joined to geometry for {closure} city."
            )
        scenario_maps[closure] = (mapped, outcomes)
        for variable in outcomes:
            pooled_values.setdefault(variable, []).append(mapped[variable])

    shared_thresholds = {
        variable: symmetric_thresholds(pd.concat(series, ignore_index=True))
        for variable, series in pooled_values.items()
    }

    for closure in closures:
        mapped, outcomes = scenario_maps[closure]
        for variable, title in outcomes.items():
            thresholds = shared_thresholds[variable]
            mapped["map_class"], labels = classified_values(
                mapped[variable], thresholds
            )
            if thresholds is None:
                number_classes = 1
                cmap = plt.matplotlib.colors.ListedColormap(["#f7f7f7"])
            else:
                number_classes = 7
                cmap = plt.get_cmap("RdBu_r", number_classes)
            fig, ax = plt.subplots(figsize=(9.0, 7.2))
            mapped.plot(
                column="map_class",
                categorical=True,
                cmap=cmap,
                linewidth=0.05,
                edgecolor="white",
                missing_kwds={"color": "#dddddd"},
                ax=ax,
            )

            # A white casing keeps the innovation visible over dark and light
            # impact classes; the black center line identifies the added link.
            if innovation is not None:
                innovation.plot(ax=ax, color="white", linewidth=1.4, zorder=5)
                innovation.plot(ax=ax, color="#111111", linewidth=0.7, zorder=6)

            ax.set_axis_off()
            ax.set_title(f"{title} — {closure} city", fontsize=14, pad=10)
            handles = [
                Patch(facecolor=cmap(i), edgecolor="none", label=label)
                for i, label in enumerate(labels)
            ]
            if innovation is not None:
                handles.append(
                    Line2D(
                        [0],
                        [0],
                        color="#111111",
                        linewidth=1.0,
                        label="Transport innovation",
                    )
                )
            ax.legend(
                handles=handles,
                title="Percent change",
                loc="center left",
                bbox_to_anchor=(1.01, 0.5),
                frameon=False,
                fontsize=9,
                title_fontsize=9,
            )
            fig.subplots_adjust(right=0.78)
            stem = f"{closure}_city_{variable}"
            fig.savefig(map_dir / f"{stem}.pdf", bbox_inches="tight")
            fig.savefig(map_dir / f"{stem}.png", dpi=250, bbox_inches="tight")
            plt.close(fig)

    print(f"Maps written to {map_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map QUETRANSPORT simulation results."
    )
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    make_maps(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
