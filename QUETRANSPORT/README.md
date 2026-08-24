# QUETRANSPORT

**A transparent, configurable toolkit for quantitative transport appraisal in spatial equilibrium.**

QUETRANSPORT integrates:

1. **GRID:** converts polygon data into a consistent spatial economy.
2. **TTMATRIX:** constructs comparable baseline and policy travel-time matrices, or validates user-provided matrices.
3. **MATLAB:** inverts a baseline equilibrium and solves transport counterfactuals under open- and closed-city closures.

The economic core follows the structure and numerical style of Ahlfeldt, Redding, Sturm and Wolf (2015, *Econometrica*, ARSW), while removing Berlin-specific dimensions, paths and inputs. It evaluates policies conditional on user-chosen parameters; it does **not** estimate structural parameters.

> **Status:** research software under active development. Validate every input and convergence diagnostic before interpreting results.

## What it does

Starting from polygon geography, population, employment and one observed floor-space rent, the toolkit:

- creates square or hexagonal cells, or retains original polygons;
- allocates extensive and intensive data using exact area intersections;
- balances aggregate employment to population;
- creates travel times before and after a transport intervention;
- recovers model-consistent wages and spatial fundamentals;
- solves counterfactuals with endogenous productivity and amenity spillovers;
- supports a **closed city**, an **open city**, or both;
- optionally adds productivity, amenity and structural-density shocks;
- exports diagnostics, local and aggregate results, and maps.

The observed rent is a **common floor-space rent**, not land rent or a regulatory wedge. Commercial and residential bid rents remain endogenous model objects. Land rent is computed separately as the residual from the developer problem.

## Three-step quick start

### 1. Supply inputs

Place source polygons in `input/raw/grid/`. Their attributes must contain population, employment and a developed/retention indicator; they may contain a common observed floor-space rent. Map exact fields in `project_config.yaml`.

For transport, either place network/station layers under `input/raw/networks/`, or place labeled matrices under `input/raw/travel_times/` and select `ttmatrix.source: user_provided`. A baseline network is optional; if absent, direct off-network travel defines the baseline. Optional policy polygons belong in `input/raw/shocks/`.

### 2. Edit one file

Edit [`project_config.yaml`](project_config.yaml), beside the master script. It is the only file a normal user changes. It controls paths, stages, GRID, TTMATRIX, structural parameters, closure, numerical settings, shocks and reporting.

Choose `grid.cell_geometry: square`, `hexagon` or `original`. With `original`, supplied polygons are retained and `cell_size_km` is ignored.

### 3. Run the master script

In Spyder, open `RUN_QUETRANSPORT.py` and press **Run**. Its own location defines the project root.

In PowerShell:

```powershell
Set-Location "D:\Dropbox\GA\_research\_TOOLKITS\QUETRANSPORT"
python .\RUN_QUETRANSPORT.py
```

The script checks and installs Python requirements, prepares and validates inputs, launches a **new** MATLAB process, runs the model, and creates reports.

For Python preparation followed by MATLAB on a server:

```powershell
python .\RUN_QUETRANSPORT.py --prepare-only
```

Copy the repository including `input/standardized/`, then run `src/matlab/scripts/run_all.m` in a new MATLAB session.

## Requirements

- Python 3 and [`requirements.txt`](requirements.txt);
- MATLAB with `readtable` and `jsondecode`;
- GIS inputs with a defined CRS;
- enough memory and disk for two dense N-by-N matrices.

Manual Python installation:

```powershell
python -m pip install -r requirements.txt
```

## Input contract

`locations.csv` defines canonical locations and ordering. Geometry, matrices and shocks must resolve to the same unique `location_id` values.

| Object | Type | GRID treatment |
|---|---|---|
| Population | Extensive | Allocate by source-area overlap and sum |
| Employment | Extensive | Allocate and sum, then balance to population |
| Common floor-space rent | Intensive | Intersection-area-weighted mean |
| Land area | Geometry-derived | Positive area in the analysis CRS |

Wages are **not** an input. MATLAB recovers workplace wages jointly with productivity and amenities so commuting reproduces observed workplace and residence employment.

See [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) for schemas, units, formulas and validation.

## Travel scenarios

With `ttmatrix.source: ttmatrix`:

- both baseline network paths `null` means a direct off-network baseline;
- both baseline layers supplied means an initial-network baseline;
- counterfactual layers describe the policy network.

With `user_provided`, both matrix paths are required and network paths are ignored. Matrices must be finite, nonnegative, labeled and square. The pipeline checks dimensions, IDs, order, diagonal treatment and change distributions before MATLAB.

## Optional primitive changes

Transport can be combined with multiplicative changes in productivity, amenities and structural density. Supply a non-overlapping shapefile or GeoPackage and map its fields under `scenario`. A value of `1.10` means +10%; `1.00` is neutral. GRID area-interpolates policy polygons to model geography and treats uncovered area as unchanged. Set `scenario.shocks_shapefile: null` for transport only.

Separate PDF and PNG maps show each imposed change with the policy boundary and transport innovation.

## Economic workflow

Conditional on fixed parameters:

1. **Quantification:** construct baseline objects and balance employment margins.
2. **Inversion:** recover productivity, amenities, structural density and wages.
3. **Counterfactual:** change travel times and optional fundamentals.
4. **Equilibrium:** solve reallocation, prices, wages, output, land rent and welfare or population.

MATLAB retains explicit damped ARSW-style fixed-point updates. It reports iteration counts and gaps. Reaching an iteration ceiling without meeting tolerance is a hard failure.

For equations, unknown/equation counting, inversion formulas, closures, land-rent accounting and pseudo-code, see the [Codebook](docs/QUETRANSPORT_CODEBOOK.pdf) ([source](docs/QUETRANSPORT_CODEBOOK.tex)).

## Outputs

| Folder | Contents |
|---|---|
| `outputs/diagnostics/` | resolved configuration, validation and convergence |
| `outputs/inversion/` | inverted fundamentals and baseline objects |
| `outputs/simulation/` | levels and percentage changes by closure |
| `outputs/tables/` | aggregate outcome tables |
| `outputs/maps/` | transport innovation, imposed shocks and effects |

Local outputs include population, employment, wages, effective wages, floor-space prices, floor space, output and land rent. Aggregate reports distinguish expected utility, population, GDP/output, wage bill and residual land rent. Welfare adjusts in the closed city; outside utility is fixed and population adjusts in the open city.

## Repository layout

```text
QUETRANSPORT/
|-- RUN_QUETRANSPORT.py
|-- project_config.yaml
|-- input/{raw,standardized}/
|-- src/{python,matlab}/
|-- docs/
|-- tests/
|-- outputs/
`-- vendor/
```

See [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) and [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Testing and computational scale

The pipeline stops on invalid IDs, geometry, quantities, matrices, overlapping shocks or solver non-convergence. Run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests\python
```

Dense matrices require N² storage and routing can be slow. Fine grids may require substantial RAM, disk and runtime. Use `--prepare-only` for server workflows.

## Documentation

- [User guide](USER_GUIDE.md)
- [Documentation index](docs/README.md)
- [Codebook](docs/QUETRANSPORT_CODEBOOK.pdf)
- [Data contract](docs/DATA_CONTRACT.md)
- [Workflow](docs/WORKFLOW.md)
- [Model architecture](docs/MODEL_ARCHITECTURE.md)
- [Status](STATUS.md)

## Model lineage

> Ahlfeldt, Gabriel M.; Redding, Stephen J.; Sturm, Daniel M.; and Wolf, Nikolaus (2015). “The Economics of Density: Evidence from the Berlin Wall.” *Econometrica* 83(6), 2127–2189.

Adapted ARSW routines are isolated under `src/matlab/functions/arsw/`; see [`vendor/README.md`](vendor/README.md).

## Citation, license and contributing

Please cite this software and ARSW. Metadata are in [`CITATION.cff`](CITATION.cff).

No public software license has yet been selected. Until one is added, all rights are reserved. Selecting a license is required before public release.

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Reports should include the resolved configuration, software versions, failing stage and diagnostics. Never post restricted data publicly.
