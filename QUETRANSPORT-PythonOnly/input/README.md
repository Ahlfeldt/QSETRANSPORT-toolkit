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
from the [AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit).

To reproduce a controlled solver-only comparison instead, populate
`input/standardized/` with the same data contract used by QUETRANSPORT and run
with `config/project_config.identical_standardized_inputs.yaml`.
