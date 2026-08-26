# Generated standardized inputs

This directory is populated automatically by GRID and TTMATRIX when
`RUN_QUETRANSPORT.py` runs. Generated location files and dense travel-time
matrices are deliberately not committed because they are reproducible from the
bundled raw inputs and can be several hundred megabytes.

A complete preparation run creates:

- `model/locations.csv`: canonical model variables and `location_id` order;
- `geography/locations.gpkg` and `.shp`: retained model polygons;
- `geography/centroids.gpkg` and `.shp`: matching routing centroids;
- `travel_times/travel_times_baseline.csv` and
  `travel_times_counterfactual.csv`: labelled dense matrices in minutes;
- `shocks/shocks.csv` and `.gpkg` when a primitive-change layer is active; and
- `runtime_config.json`: the resolved, run-specific configuration used by the
  economic model.

Do not edit these files or combine files produced by different runs. Every
table and geometry uses the canonical `location_id` set defined by
`model/locations.csv`; matrix row and column order follows the same IDs. The
contract is identical to the mixed toolkit's
[standardized data contract](../../../QUETRANSPORT/docs/DATA_CONTRACT.md).
