# QUETRANSPORT-PythonOnly codebook

## Purpose

QUETRANSPORT-PythonOnly provides a push-button Python workflow for appraising
transport improvements, changes in urban fundamentals, or both within a
quantitative urban model. It uses the same raw inputs, standardized contract,
economic parameters, scenarios and reported measures as the mixed toolkit.

## Required raw inputs

The minimum geography contains polygon geometry, population, employment and a
developed/retention variable. An observed common floor-space rent is optional;
otherwise the configured synthetic-rent rule is used. Every spatial file must
declare a CRS. See the [input guide](../input/README.md) for exact formats and
the [data contract](DATA_CONTRACT.md) for standardized schemas.

Travel times may be constructed from line and station layers or supplied as
two labelled square matrices. Both paths in a network pair must be present or
both null. Null counterfactual paths reuse baseline travel times, permitting a
fundamentals-only experiment.

## Optional primitive changes

Policy polygons may impose multiplicative hats on fundamental productivity,
fundamental amenities and structural density. A value of `1.10` denotes a 10%
increase; `1.00` is neutral. Exact overlap shares attribute changes to model
cells, and uncovered cell area contributes the neutral value.

## Baseline inversion

The inversion takes observed population, balanced employment, floor-space
rent, land area and baseline travel costs as given. It recovers model-consistent
wages, productivity, amenities, structural density and other baseline objects
so the model reproduces residence and workplace employment under the configured
parameters.

## Counterfactual scenarios

The toolkit reports closed-city, open-city and fixed-distribution results. It
can repeat all three after switching off productivity and amenity spillovers.
Transport and primitive changes enter the same counterfactual, so their joint
general-equilibrium effects can be evaluated.

## Main aggregate measures

| Measure | Interpretation |
|---|---|
| Expected utility | Welfare change under the selected city closure. |
| Population | Change in city population; zero by construction in a closed city. |
| GDP | Change in aggregate urban output. |
| Total land rent | Change in the developer-residual value of land. |
| Immediate commute-time change | Network effect holding baseline OD assignments fixed. |
| Post-relocation commute-time change | Mean change after endogenous residence-workplace relocation. |
| Total commuter-minutes change | Change in aggregate travel time including population adjustment. |

Local CSVs and maps report percentage changes in population, employment,
wages, output, floor-space prices and annual land rent. Diagnostics document
GRID allocation, travel matrices, convergence and configuration choices.

## Reproducibility and citation

Run the root `RUN_QUETRANSPORT.py` without editing source code. Archive the raw
inputs, `project_config.yaml`, resolved runtime configuration and diagnostics
with substantive results. Citation information is provided in
[`CITATION.cff`](../CITATION.cff); the toolkit also asks users to cite the ARSW
paper underlying the methodology.
