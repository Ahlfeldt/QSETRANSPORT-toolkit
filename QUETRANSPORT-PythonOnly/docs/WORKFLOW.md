# Implemented Python-only workflow

`RUN_QUETRANSPORT.py` executes one cumulative Python workflow. Every stage uses
the canonical `location_id` ordering established by GRID.

## Stage 0: configuration

The root `project_config.yaml` is validated and resolved relative to the toolkit
root. The resolved snapshot is saved as `input/standardized/runtime_config.json`.

## Stage 1: GRID

GRID creates square or hexagonal cells, or retains the original source
polygons. Population and employment are allocated as extensive quantities;
rent and the developed indicator are intensive. Employment is balanced to
population. Locations, polygons and centroids are exported and validated.

## Stage 2: TTMATRIX

TTMATRIX constructs baseline and counterfactual matrices from centroids and
network layers, or validates two user-provided labelled matrices. Null baseline
network paths mean direct off-network baseline travel. Null counterfactual
network paths copy the complete baseline matrix for a fundamentals-only
experiment.

## Stage 3: optional primitive changes

Policy polygons provide multiplicative changes in productivity, amenities and
structural density. Exact target-area attribution maps them to model cells;
uncovered area remains unchanged and overlapping policy polygons are rejected.

## Stage 4: Python baseline inversion

`src/python/scripts/invert_baseline.py` loads the standardized data and calls
the functions in `functions/inversion/`. The solver recovers productivity,
amenities, model-consistent wages, structural density and related baseline
objects while reproducing observed residence and workplace employment.

## Stage 5: Python counterfactuals

`functions/equilibrium/` solves closed-city, open-city and fixed-distribution
scenarios. The optional no-spillover comparison performs a separate baseline
inversion with productivity and amenity spillovers set to zero before rerunning
all scenarios. Main and sensitivity inversions are never mixed.

## Stage 6: reporting

Python writes local outcomes, aggregate tables, diagnostics and maps. Aggregate
reporting distinguishes immediate commute-time change, post-relocation
commute-time change and total commuter-minutes change. The fixed-distribution
scenario also reports a worker-welfare decomposition.

## Execution options

- `python RUN_QUETRANSPORT.py`: complete raw-to-results run.
- `python RUN_QUETRANSPORT.py --prepare-only`: GRID and TTMATRIX only.
- `python src/python/run_pipeline.py --model-only`: use existing standardized inputs.
- `python src/python/run_pipeline.py --model-only --skip-maps`: solver comparison without map regeneration.

Dense travel and commuting matrices scale with the square of the number of
locations. Use a coarser grid or a machine with more memory for large cities.
