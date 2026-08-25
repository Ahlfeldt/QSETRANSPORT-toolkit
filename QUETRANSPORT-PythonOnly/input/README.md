# Input data

User data are deliberately not committed to the repository.

For the default raw-to-results workflow, place files under:

```text
input/raw/grid/
input/raw/networks/baseline/          # optional
input/raw/networks/counterfactual/
input/raw/travel_times/               # for user-provided matrices
input/raw/shocks/                     # optional primitive changes
```

Then map filenames and source fields in `project_config.yaml`. GRID and
TTMATRIX create `input/standardized/` automatically.

Ready-made population and employment grids for many cities can be downloaded
from the [AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit). Convenient
map-illustrated dropdown menus provide downloads for
[381 US metropolitan areas](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-381-us-msas?authuser=0)
and
[125 global cities](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-125-global-cities?authuser=0).

To reproduce a controlled solver-only comparison instead, populate
`input/standardized/` with the same data contract used by QUETRANSPORT and run
with `config/project_config.identical_standardized_inputs.yaml`.
