# Model and numerical architecture

## Relationship to ARSW

The toolkit should preserve the economic structure and recognizable numerical style of the ARSW code while removing Berlin-specific dimensions, paths, globals, and hard-coded parameter values. Reuse is selective: each legacy function must be audited for assumptions before it is copied or adapted.

Likely reusable concepts include the commuting probability system, market-clearing updates, fundamental inversion, endogenous productivity/amenity feedbacks, and the open- and closed-city fixed-point solvers. The general toolkit must not simply wrap a Berlin-sized state vector.

## One endogenous solver family

Only one counterfactual solver family is implemented. It supports endogenous productivity and amenities through spillover coefficients. A zero coefficient removes that feedback, so separate “exogenous” and “endogenous” code paths are unnecessary.

This avoids duplicated logic and makes comparisons exact: the same equations, tolerances, and update order are used in all cases.

## City closure

The project configuration exposes `city_closure`:

### Closed city

- Aggregate population is fixed at its baseline model total.
- Residents reallocate across locations.
- Expected utility adjusts and is a key aggregate welfare outcome.

### Open city

- Outside/reservation utility is fixed at the baseline-inverted value.
- Aggregate population adjusts through migration.
- Total population is a key aggregate outcome; welfare reporting must respect the closure rather than treating utility as freely varying.

The two closures should share lower-level update functions and differ only in the outer equilibrium condition, following the structure of the ARSW `smodendog` and `ussmodendog` logic.

## MATLAB source organization

Entry scripts in `src/matlab/scripts`:

- `invert_baseline.m`;
- `run_counterfactual.m`;


All callable functions live in `src/matlab/functions`. No local or nested function definitions belong at the bottom of master scripts. Mapping helpers live in `src/matlab/mapping` because plotting is not part of the equilibrium algorithm.

Each teaching script will have conspicuous sections for:

1. paths and configuration;
2. data reading and validation;
3. parameter loading;
4. baseline construction;
5. inversion;
6. simulation;
7. relative changes;
8. saving and mapping.

## Fixed-point style

The numerical implementation should retain ARSW conventions:

- initialize economic objects explicitly;
- update blocks in an economically interpretable sequence;
- apply visible damping coefficients;
- compute named gaps after each update;
- print or store iteration counts and gaps;
- stop only when every required gap meets tolerance;
- fail with an informative message at the iteration ceiling;
- save a convergence trace for diagnosis.

Safe defaults belong in configuration, but advanced users may override them. Numerical controls must not be confused with estimated economic parameters.

## One observed rent and two endogenous bid rents

The standardized baseline input contains one common floor-space rent. The adapter passes that same observed value into the commercial and residential inversion equations. It is neither land rent nor an inferred regulatory wedge, and missing values stop the pipeline rather than trigger imputation.

The ARSW equilibrium structure is retained after inversion:

- commercial demand determines the endogenous commercial bid rent `q`;
- residential demand determines the endogenous residential bid rent `Q`;
- no arbitrage imposes `q = Q` in mixed-use locations;
- the two bid rents may differ at specialized corner locations;
- annual land rent is separately derived as the developer residual.

Thus the one-rent input is a transparent maintained baseline-data restriction. It does not collapse the two endogenous land-use markets in the counterfactual model.

## Land value
Residual land rent is derived from the developer’s profit condition and is not the sum of floor-space rents. Aggregate land value must therefore be constructed from the model-consistent residual land-rent object and land area. The construction land share must be explicitly parameterized; it must not inherit an incorrect hard-coded share.

## Configuration rather than source edits

MATLAB will read one resolved JSON snapshot generated from the user's project_config.yaml. Users choose GRID, TTMATRIX, economic parameters, closure, shocks, and numerical options only in that YAML file. The master script should run unchanged across cities and block structures.

## Integration boundaries

- GRID exports standardized locations and geography.
- TTMATRIX exports labeled baseline and counterfactual matrices.
- MATLAB consumes only standardized files and never reaches into the internal working directories of the upstream tools.
- Reporting consumes saved MATLAB outputs and geometry, not live solver state.

This boundary keeps the pipeline cumulative while allowing each component to be tested and replaced independently.
