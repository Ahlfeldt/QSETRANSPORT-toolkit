# Implemented cumulative workflow

QUETRANSPORT is modular but cumulative. GRID, TTMATRIX, MATLAB and reporting communicate through documented files keyed by `location_id`.

## Stage 0: configuration

The root `project_config.yaml` is validated and resolved relative to the repository root. A JSON snapshot is written for MATLAB and copied to diagnostics.

## Stage 1: GRID

GRID reads source polygons, maps declared attributes, creates square/hexagonal cells or retains original polygons, and performs exact area-based attribution. Population and employment are extensive; rent and the retention indicator are intensive. It balances employment to population and exports locations, polygons and centroids.

**Gate:** unique IDs, valid CRS and geometry, positive required data, balanced totals, and matching geography.

## Stage 2: TTMATRIX

TTMATRIX either constructs baseline/counterfactual travel times from centroids
and network layers or validates labeled user matrices. Null counterfactual
paths copy the complete baseline matrix for a fundamentals-only experiment.

The default `standalone_ttmatrix` method matches the standalone toolkit. It
snaps nearby network endpoints, retains every network coordinate as a graph
vertex, connects stations to their nearest network vertex with the documented
small positive weight, connects each location to three stations and five
location neighbours at walking speed, and runs weighted NetworkX Dijkstra from
each origin. A no-network baseline uses the same nearest-neighbour walking
graph. The graph can contain disconnected walking components or sparse-graph
detours; diagnostics record component counts, unreachable OD pairs, and detour
ratios. These limitations are reported rather than repaired by adding edges.

The selectable `direct_station_access` method retains the earlier
toolkit assumptions: straight-line direct travel is always available and each
OD pair is compared with station access, network travel and egress. It can
consider all stations and does not use the sparse location-neighbour graph.
The two routing methods are substantively different and are not described as
numerically equivalent.

**Gate:** square finite matrices with the exact location IDs and order.

## Stage 3: optional primitive shocks

Policy polygons in arbitrary units are intersected with model polygons. Multiplicative hats for productivity, amenities and structural density are attributed by target-area shares; uncovered area has hat one. Overlapping policy polygons are rejected. A null path produces neutral shocks.

**Gate:** finite positive hats and matching standardized IDs. Maps provide a visual check.

## Stage 4: baseline inversion

MATLAB reads only standardized inputs and the resolved configuration. It constructs observed objects and iterates on productivity and amenities while recovering model-consistent wages until commuting reproduces workplace and residence employment. It derives structural density and the remaining primitives conditional on parameters.

An inner ARSW inversion pass has 199 iterations. If needed, the wrapper restarts from the latest vectors up to `maximum_inversion_passes`. Exhausting all passes is a hard failure.

**Gate:** convergence, employment-margin reproduction and valid inverted objects.

## Stage 5: counterfactual equilibrium

The policy travel matrix and optional primitive hats replace baseline objects. Endogenous productivity and amenity feedbacks remain in one solver family; setting their spillover coefficients to zero switches them off.

- **Closed city:** total population is fixed and expected utility adjusts.
- **Open city:** outside utility is fixed and total population adjusts.
- **Fixed distribution:** baseline OD assignments, local population and
  employment, rents, and land allocation remain fixed. Travel times still
  change commuting costs and transport-mediated productivity and amenity
  kernels. This is an accounting benchmark rather than a market-clearing
  closure.

When `project.run_no_spillover_comparison` is true, MATLAB separately
re-inverts the baseline with both spillover elasticities set to zero and reruns
all three scenarios. The main and sensitivity inversions are never mixed.

Solvers print iteration counts and current gaps. Because the convergence iteration is unknown, these messages are diagnostics rather than percentage-complete progress bars.

**Gate:** all gaps below tolerance and equilibrium/accounting checks passed.

## Stage 6: reporting

The pipeline saves levels, local percentage changes, aggregates and maps.
Aggregate reporting distinguishes immediate commute-time change,
post-relocation commute-time change, and total commuter-minutes change. The
fixed-distribution benchmark additionally saves a worker-welfare decomposition.
Transport innovation is overlaid on impact maps. The one-rent baseline
restriction does not turn floor-space rent into land rent: annual land rent is
reported from the developer residual.

## Reproducibility and scale

Every stage is controlled by the root configuration. Dense output matrices
scale as N squared, while routing avoids constructing an N-by-N candidate
matrix for every station pair. `--prepare-only` supports preparation on one
machine and MATLAB on a server while preserving the standardized contract.
