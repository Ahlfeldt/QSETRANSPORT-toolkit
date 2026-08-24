# MATLAB source

## Entry scripts

- `scripts/run_all.m`: complete inversion and simulation workflow.
- `scripts/invert_baseline.m`: baseline input loading and inversion.
- `scripts/run_counterfactual.m`: requested closure simulations and reporting.

## Functions

- `functions/io/`: resolved configuration and standardized input readers.
- `functions/inversion/`: baseline inversion wrapper.
- `functions/equilibrium/`: shocks and city-closure wrappers.
- `functions/reporting/`: percentage changes, tables and iteration/gap messages.
- `functions/arsw/`: audited adapted ARSW numerical routines.

Functions remain separate from scripts. Normal users select parameters, closure, shocks and numerical controls in the root YAML; MATLAB reads the generated runtime JSON. Non-convergence is an error and no result should be presented as solved.
