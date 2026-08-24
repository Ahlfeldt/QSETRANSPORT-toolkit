# Project status

## Implemented

- cumulative GRID–TTMATRIX–MATLAB–reporting pipeline;
- one root master script and one root user configuration;
- square, hexagonal and original-polygon geography;
- exact area-based attribution for extensive and intensive variables;
- optional TTMATRIX construction or user-provided matrices;
- optional baseline network and required policy network when routing;
- one common observed baseline floor-space rent, with an explicit synthetic fallback;
- model-consistent wage recovery inside baseline inversion;
- optional polygon shocks to productivity, amenities and structural density;
- ARSW-style inversion with repeated passes and hard failure on non-convergence;
- open- and closed-city counterfactuals;
- local and aggregate tables, transport/shock/equilibrium maps;
- Python tests for interpolation, original geography and shocks;
- model codebook and repository documentation.

The pipeline has been exercised with the MRRH2018 raw GRID/transport inputs. Those restricted or large inputs are not a redistributable example.

## Required before a public release

- select and add a public software license;
- add the final repository URL to `CITATION.cff`;
- add a small redistributable end-to-end example;
- add MATLAB regression tests and a documented supported-version matrix;
- confirm provenance and redistribution terms for every adapted routine;
- remove generated and user-owned data from version control;
- create a tagged release after a clean-machine reproduction test.

## Current modeling restrictions

- parameters are supplied rather than estimated;
- the baseline uses one common observed floor-space rent, not separate observed use-specific rents;
- no regulatory-wedge primitive or wedge shock is implemented;
- matrices are dense and therefore scale in memory as N squared;
- benefit-cost analysis requires externally supplied monetary assumptions and is not inferred automatically.
