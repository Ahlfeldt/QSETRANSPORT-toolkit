# QUETRANSPORT-PythonOnly

***Transport appraisal with a quantitative urban model—entirely in Python.***

QUETRANSPORT-PythonOnly implements the complete QUETRANSPORT workflow in
Python: spatial-data preparation, travel-time construction, baseline inversion,
quantitative urban-model counterfactuals, validation, tables, and maps.
**MATLAB is not required.**

It retains the same conceptual stages, data contracts, model closures, and
outputs as [`QUETRANSPORT`](../QUETRANSPORT/). Its organization deliberately
mirrors the MATLAB implementation: scripts orchestrate tasks, while reusable
calculations live in separate function folders.

> **Beta status:** the Python implementation has been validated against the
> MATLAB reference using identical raw and standardized inputs. All six
> scenarios, three travel-time measures, the welfare decomposition, and 3,577
> location-level results agree closely. Further testing across additional cities
> and model configurations remains advisable before production appraisal.

## Structure

```text
RUN_QUETRANSPORT.py
project_config.yaml
src/python/
├── run_pipeline.py
├── scripts/
│   ├── invert_baseline.py
│   ├── run_counterfactual.py
│   ├── run_no_spillovers.py
│   └── run_all.py
└── functions/
    ├── io/
    ├── inversion/
    ├── equilibrium/
    └── reporting/
```

The retained `grid`, `ttmatrix`, and mapping modules prepare the same
standardized inputs and outputs as the mixed Python–MATLAB toolkit. The
`functions/inversion` and `functions/equilibrium` folders replace its MATLAB
economic-model stage.

## Run

The repository includes the raw example inputs used by the reference
QUETRANSPORT application, so the default configuration can be run immediately
and compared one-to-one with the mixed Python–MATLAB version. For a new
application, download a ready-made city grid from the
[AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit). Convenient
map-illustrated dropdown menus provide grid downloads for
[381 US metropolitan areas](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-381-us-msas?authuser=0)
and
[125 global cities](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-125-global-cities?authuser=0).
Alternatively, replace the example with compatible polygon data and
transport-network layers under `input/raw/`. The default
configuration runs GRID and TTMATRIX, generates standardized inputs locally,
solves the Python model, and writes results to `outputs/`.

The optional
[`config/project_config.identical_standardized_inputs.yaml`](config/project_config.identical_standardized_inputs.yaml)
configuration skips GRID and TTMATRIX. It supports controlled solver comparisons
when a user has already supplied identical standardized inputs.

Open `RUN_QUETRANSPORT.py` in Spyder and press **Run**, or execute:

```powershell
python .\RUN_QUETRANSPORT.py
```

Useful advanced options:

```powershell
python .\src\python\run_pipeline.py --prepare-only
python .\src\python\run_pipeline.py --model-only --skip-maps
```

## Implemented in this first version

- standardized location and travel-matrix readers;
- baseline OD balancing and inversion of model primitives;
- endogenous productivity and amenity spillovers;
- closed- and open-city equilibrium fixed points;
- fixed-distribution accounting benchmark;
- optional re-inversion with spillovers set to zero;
- the three clearly labelled travel-time measures used by QUETRANSPORT:
  immediate commute-time change, post-relocation commute-time change, and
  total commuter-minutes change;
- local outcome tables, aggregate results, and welfare decomposition;
- the existing GRID, TTMATRIX, scenario, and mapping preparation stages.

## Requirements

- Python 3.11 or newer is recommended;
- packages listed in [`requirements.txt`](requirements.txt), including NumPy,
  pandas, SciPy, GeoPandas, Pyogrio, Shapely, NetworkX, Matplotlib, and PyYAML;
- sufficient RAM for dense N-by-N travel and commuting matrices.

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

No MATLAB installation or MATLAB toolbox is required.

## Validation against QUETRANSPORT

The Python-only workflow was run independently from the same 26 raw files used
by the mixed implementation. GRID and TTMATRIX reproduced byte-identical
location and travel-time CSVs. Across the economic-model outputs:

- the largest aggregate headline difference was approximately **0.0012
  percentage points**;
- spatial correlations for endogenous closed- and open-city outcomes generally
  exceeded **0.99998**;
- fixed-distribution location results were numerically identical to practical
  precision; and
- rerunning the complete raw-to-results Python workflow reproduced the earlier
  solver-validation CSVs byte for byte.

Small remaining differences reflect numerical normalization, damping, and
stopping rules rather than different substantive model equations.

## Citation

Please cite QUETRANSPORT-PythonOnly in the same way as QUETRANSPORT:

> Ahlfeldt, Gabriel M. (2026). *QUETRANSPORT: A Toolkit for Transport Appraisal
> with a Quantitative Urban Model* (Version 0.1.0) [Computer software].
> https://github.com/Ahlfeldt/QSETRANSPORT-toolkit

Please also cite the underlying methodology:

Ahlfeldt, G. M., Redding, S. J., Sturm, D. M., and Wolf, N. (2015), “The
Economics of Density: Evidence from the Berlin Wall,” *Econometrica*, 83(6),
2127–2189. https://doi.org/10.3982/ECTA10876

Machine-readable metadata are provided in [`CITATION.cff`](CITATION.cff) and
are intentionally the same as for the baseline QUETRANSPORT toolkit.
