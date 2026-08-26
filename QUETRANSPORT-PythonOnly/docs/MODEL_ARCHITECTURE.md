# Python-only model architecture

The Python-only toolkit implements the same quantitative urban model and data
contract as QUETRANSPORT without MATLAB. Scripts orchestrate the workflow;
reusable numerical and reporting functions live in separate modules.

## Source layout

| Module | Responsibility |
|---|---|
| `common/` | Configuration, identifiers, scenarios and progress reporting. |
| `grid/` | Spatial standardization and exact area attribution. |
| `ttmatrix/` | Network-based construction or validation of travel matrices. |
| `functions/io/` | Typed loading of standardized model data and matrices. |
| `functions/inversion/` | Baseline inversion and recovered primitives. |
| `functions/equilibrium/` | Closed, open and fixed-distribution counterfactuals. |
| `functions/reporting/` | Result tables and aggregate accounting. |
| `reporting/` | Geographic maps and imposed-shock visual checks. |
| `scripts/` | Thin user-facing stage orchestration. |

## Economic scenarios

- **Closed city:** total population is fixed and expected utility changes.
- **Open city:** outside utility is fixed and total population changes.
- **Fixed distribution:** residence-workplace assignments and local quantities
  remain fixed while travel costs and transport-mediated spillover kernels can
  change. It is an accounting benchmark rather than a market-clearing closure.

The no-spillover specification sets both spillover elasticities to zero and
re-inverts the baseline before simulation. Primitive changes are multiplicative
hats: one is neutral, values above one increase a fundamental and values below
one reduce it.

## Numerical and reproducibility rules

The canonical location set and order come from `locations.csv`. Every matrix is
reordered and validated by labels. Nonfinite or negative travel times, invalid
geometries, unmatched identifiers and nonconvergence are hard failures. Each
run saves its resolved configuration and validation diagnostics so results can
be traced to inputs and numerical choices.
