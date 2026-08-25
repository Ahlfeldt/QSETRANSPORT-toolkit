# MATLAB source

## Entry scripts

- `scripts/run_all.m`: complete inversion and simulation workflow.
- `scripts/invert_baseline.m`: baseline input loading and inversion.
- `scripts/run_counterfactual.m`: requested equilibrium closures,
  fixed-distribution benchmark, and reporting.
- `scripts/run_no_spillovers.m`: separate re-inversion and rerun of all three
  scenarios with productivity and amenity spillovers switched off.

## Functions

- `functions/io/`: resolved configuration and standardized input readers.
- `functions/inversion/`: baseline inversion wrapper.
- `functions/equilibrium/`: shocks, city-closure wrappers, and the
  fixed-distribution accounting benchmark.
- `functions/reporting/`: percentage changes, scenario tables, three
  travel-time measures, and iteration/gap messages.
- `functions/arsw/`: audited adapted ARSW numerical routines.

Functions remain separate from scripts. Normal users select parameters, closure, shocks and numerical controls in the root YAML; MATLAB reads the generated runtime JSON. Non-convergence is an error and no result should be presented as solved.
