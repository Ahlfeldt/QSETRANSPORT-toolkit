# Input data

The raw inputs for the reference application are committed here so the
Python-only and mixed Python–MATLAB toolkits can be run from the same source
data and their outputs compared one-to-one. Generated standardized inputs are
not committed; GRID and TTMATRIX recreate them during a normal run.

For another application, replace or add files under:

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
