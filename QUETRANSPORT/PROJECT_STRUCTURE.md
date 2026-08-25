# Repository structure

```text
QUETRANSPORT/
|-- README.md
|-- RUN_QUETRANSPORT.py
|-- project_config.yaml
|-- requirements.txt
|-- CONTRIBUTING.md
|-- CITATION.cff
|-- config/                     # optional example configurations
|-- docs/                       # codebook and technical documentation
|-- input/
|   |-- raw/
|   |   |-- grid/
|   |   |-- networks/{baseline,counterfactual}/
|   |   |-- travel_times/
|   |   `-- shocks/
|   `-- standardized/
|       |-- geography/
|       |-- model/
|       |-- travel_times/
|       `-- shocks/
|-- src/
|   |-- python/
|   |   |-- common/
|   |   |-- grid/
|   |   |-- ttmatrix/
|   |   `-- reporting/
|   `-- matlab/
|       |-- scripts/
|       |-- functions/{io,inversion,equilibrium,reporting,arsw}/
|       `-- mapping/
|-- tests/
|-- outputs/{diagnostics,inversion,simulation,tables,maps}/
|   `-- no_spillovers/{inversion,simulation}/
`-- vendor/
```

## User-facing root

`RUN_QUETRANSPORT.py` is the only normal entry point. `project_config.yaml` is the only normal user-edited file. Examples live under `config/` so they do not compete with the active configuration.

## Data boundaries

`input/raw/` contains user-owned files. GRID and TTMATRIX write only to `input/standardized/`. MATLAB consumes only the standardized interface and the resolved JSON configuration. Reporting reads saved results and matching geometry rather than solver state.

Raw inputs, standardized data and outputs are ignored by Git by default because they can be large, restricted or application-specific. Add redistributable examples deliberately under a separately documented example folder.

## Source boundaries

Python prepares geography, matrices, shocks, validation and maps. MATLAB performs inversion, equilibrium simulation and economic reporting. MATLAB functions are separate files, never nested at the bottom of entry scripts. Adapted ARSW routines are isolated so provenance and changes can be audited.

## Output boundaries

Diagnostics, inversion, simulation, tables and maps have separate folders. Every run should preserve a resolved configuration snapshot so numerical results can be traced to user choices.
