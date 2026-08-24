"""Map exogenously imposed primitive changes before MATLAB is run."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D

from reporting.make_maps import _transport_innovation


class ShockMapError(ValueError):
    """Raised when standardized shock geography cannot be mapped."""


MAP_DEFINITIONS = (
    ("productivity_hat", "Fundamental productivity", "imposed_fundamental_productivity"),
    ("amenity_hat", "Fundamental amenity", "imposed_fundamental_amenity"),
    ("structural_density_hat", "Structural density", "imposed_structural_density"),
)


def make_shock_maps(
    config: dict[str, Any], scenario_report: dict[str, Any]
) -> tuple[Path, ...] | None:
    """Create three separate visual checks of area-interpolated primitive hats."""
    if not scenario_report.get("active"):
        return None

    standardized_path = Path(scenario_report["standardized_geography"])
    source_path = Path(scenario_report["source_file"])
    if not standardized_path.is_file():
        raise ShockMapError(f"Standardized shock geography not found: {standardized_path}")
    if not source_path.is_file():
        raise ShockMapError(f"Source shock geography not found: {source_path}")

    mapped = gpd.read_file(standardized_path, layer="shocks")
    layer = config.get("scenario", {}).get("shocks_layer")
    source = gpd.read_file(source_path, layer=layer) if layer else gpd.read_file(source_path)
    if mapped.crs is None or source.crs is None:
        raise ShockMapError("Shock maps require coordinate reference systems.")
    source = source.to_crs(mapped.crs)
    innovation = _transport_innovation(config, mapped.crs)

    # Convert multiplicative hats to percentage changes for intuitive legends.
    for column, _, _ in MAP_DEFINITIONS:
        if column not in mapped.columns:
            raise ShockMapError(f"Standardized shock geography lacks {column}.")
        mapped[f"{column}_pct"] = 100.0 * (mapped[column].astype(float) - 1.0)

    output_dir = Path(config["paths"]["output"]) / "maps"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove the obsolete bundled figure so users do not mistake it for current
    # output after switching to the clearer one-map-per-primitive design.
    for extension in ("pdf", "png"):
        old_path = output_dir / f"imposed_primitive_changes.{extension}"
        if old_path.exists():
            old_path.unlink()

    cmap = plt.get_cmap("RdBu_r")
    output_paths: list[Path] = []
    for column, title, stem in MAP_DEFINITIONS:
        fig, axis = plt.subplots(figsize=(9.0, 7.2), constrained_layout=True)
        values = mapped[f"{column}_pct"].to_numpy(dtype=float)
        maximum = float(np.nanmax(np.abs(values))) if len(values) else 0.0

        if maximum <= 1.0e-12:
            mapped.plot(ax=axis, color="#eeeeee", edgecolor="white", linewidth=0.08)
            axis.text(
                0.5, 0.035, "No imposed change", transform=axis.transAxes,
                ha="center", va="bottom", fontsize=10,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85},
            )
        else:
            norm = TwoSlopeNorm(vmin=-maximum, vcenter=0.0, vmax=maximum)
            mapped.plot(
                ax=axis,
                column=f"{column}_pct",
                cmap=cmap,
                norm=norm,
                edgecolor="white",
                linewidth=0.08,
            )
            colorbar = fig.colorbar(
                ScalarMappable(norm=norm, cmap=cmap),
                ax=axis,
                orientation="horizontal",
                fraction=0.046,
                pad=0.025,
            )
            colorbar.set_label("Imposed change (%)", fontsize=9)
            colorbar.ax.tick_params(labelsize=8)

        # Gray outlines show the arbitrary user-provided policy units. Fine cell
        # outlines expose the spatial resolution of the area interpolation.
        source.boundary.plot(ax=axis, color="#555555", linewidth=0.35, alpha=0.75)
        mapped.boundary.plot(ax=axis, color="#777777", linewidth=0.06, alpha=0.25)

        # A white casing preserves visibility over both red and blue impact cells.
        if innovation is not None:
            innovation.plot(ax=axis, color="white", linewidth=1.4, zorder=8)
            innovation.plot(ax=axis, color="#111111", linewidth=0.7, zorder=9)

        axis.set_title(f"Imposed change in {title.lower()}", fontsize=14, pad=10)
        axis.set_axis_off()
        axis.set_aspect("equal")
        legend_handles = [
            Line2D(
                [0], [0], color="#555555", linewidth=0.7,
                label="Policy-polygon boundary",
            )
        ]
        if innovation is not None:
            legend_handles.append(
                Line2D(
                    [0], [0], color="#111111", linewidth=1.0,
                    label="Transport innovation",
                )
            )
        axis.legend(
            handles=legend_handles,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=len(legend_handles),
            frameon=False,
            fontsize=9,
        )

        pdf_path = output_dir / f"{stem}.pdf"
        png_path = output_dir / f"{stem}.png"
        fig.savefig(pdf_path, bbox_inches="tight")
        fig.savefig(png_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        output_paths.extend((pdf_path, png_path))

    return tuple(output_paths)