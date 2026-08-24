# Contributing to QUETRANSPORT

QUETRANSPORT uses strict interfaces between GRID, TTMATRIX, MATLAB and reporting. Contributions should preserve them and keep normal-user choices in the root `project_config.yaml`.

## Conventions

- Put Python modules under the appropriate `src/python/` component.
- Keep MATLAB entry scripts short and sectioned; callable functions belong in separate files under `src/matlab/functions/`.
- Preserve explicit ARSW-style updates, named gaps and hard failure on non-convergence.
- Never add city-specific dimensions, absolute paths or unexplained parameter values to source code.
- Join spatial and matrix objects by `location_id`; never rely on incidental row order.
- Keep floor-space rent, endogenous bid rents and residual land rent distinct.
- Document new configuration keys in the root configuration, README, data contract and codebook.

## Validation

Run:

```powershell
python -m pytest tests\python
```

For MATLAB changes, verify baseline inversion, both employment margins, baseline reproduction, requested closures, accounting identities and zero-shock nesting. Compile and inspect the codebook after LaTeX changes.

Do not commit confidential inputs, generated outputs, caches or large matrices. A pull request should explain the economic or computational change, affected interfaces, tests and numerical comparisons.
