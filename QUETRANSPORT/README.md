# QUETRANSPORT

***A Toolkit for Transport Appraisal with a Quantitative Urban Model.***

**Version 0.1.0 (beta)** · **Author: [Gabriel M. Ahlfeldt](https://www.ahlfeldt.com/)**

> **Download a grid. Configure. Push Run.** QUETRANSPORT is compatible with
> ready-made population and employment grids for **381 US metropolitan areas**
> and **125 global cities** available from the
> [AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit). Convenient
> map-illustrated dropdown menus provide downloads for
> [381 US metropolitan areas](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-381-us-msas?authuser=0)
> and
> [125 global cities](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-125-global-cities?authuser=0).
> Users can select a city grid, describe a transport improvement, edit one
> configuration file, and produce validated maps, aggregate statistics, and
> diagnostics.

QUETRANSPORT integrates:

1. [**GRID**](https://github.com/Ahlfeldt/GRID-toolkit): converts polygon data into a consistent spatial economy.
2. [**TTMATRIX**](https://github.com/Ahlfeldt/TTMATRIX-toolkit): constructs comparable baseline and policy travel-time matrices, or validates user-provided matrices.
3. **MATLAB:** inverts a baseline equilibrium and solves transport counterfactuals under open- and closed-city closures.

The economic core follows the structure and numerical style of Ahlfeldt, Redding, Sturm and Wolf (2015, *Econometrica*, ARSW), building on the [ARSW2015 toolkit](https://github.com/Ahlfeldt/ARSW2015-toolkit) while removing Berlin-specific dimensions, paths and inputs. It evaluates policies conditional on user-chosen parameters; it does **not** estimate structural parameters.

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
- reports a **fixed-distribution accounting benchmark** holding baseline
  residence-workplace assignments and local employment distributions fixed;
- optionally re-inverts and reruns every scenario with productivity and amenity
  spillovers switched off;
- optionally adds productivity, amenity and structural-density shocks;
- exports diagnostics, local and aggregate results, and maps.

The observed rent is a **common floor-space rent**, not land rent or a regulatory wedge. Commercial and residential bid rents remain endogenous model objects. Land rent is computed separately as the residual from the developer problem.

## Three-step quick start

### 1. Supply inputs

For the shortest route to a working application, download a city grid from the
[AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit), using the convenient
map-illustrated dropdown menu for
[381 US metropolitan areas](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-381-us-msas?authuser=0)
or
[125 global cities](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-125-global-cities?authuser=0).
Alternatively, use your own polygon geography. Place source polygons in `input/raw/grid/`. Their
attributes must contain population, employment and a developed/retention
indicator; they may contain a common observed floor-space rent. Map exact fields
in `project_config.yaml`.

For transport, either place network/station layers under `input/raw/networks/`, or place labeled matrices under `input/raw/travel_times/` and select `ttmatrix.source: user_provided`. A baseline network is optional; if absent, direct off-network travel defines the baseline. Optional policy polygons belong in `input/raw/shocks/`. The [input guide](input/README.md) gives the exact geography, field, CRS, network and matrix requirements and a checklist for replacing the example city.

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

### Python

- **Python 3**; a current 64-bit release is recommended.
- Python packages from [`requirements.txt`](requirements.txt): NumPy, pandas,
  PyYAML, GeoPandas, Pyogrio, Shapely, Matplotlib, SciPy, NetworkX, and tqdm.
- For development and tests, install the additional packages in
  [`requirements-dev.txt`](requirements-dev.txt), including pytest.

The Python environment performs all geospatial processing and map production.
GeoPandas, Pyogrio, and Shapely provide the required GIS functionality; SciPy
and NetworkX support distance and network calculations. A separate desktop GIS
application is not required.

### MATLAB

- **MATLAB** with support for `string`, `jsondecode`, `readtable`, and
  `writetable`; a current 64-bit release is recommended.
- **No additional MATLAB toolboxes are required by the current code.** In
  particular, QUETRANSPORT does not currently call the Mapping Toolbox,
  Optimization Toolbox, Global Optimization Toolbox, or Statistics and Machine
  Learning Toolbox. Spatial preparation and mapping take place in Python.

The MATLAB version and supported operating-system matrix have not yet been
formally validated across releases. If deploying the toolkit on a server, use a
recent MATLAB release and first reproduce the baseline example before running a
new application.

### Data and hardware

- Every GIS input must have a defined coordinate reference system (CRS).
- The machine must have enough memory and disk space for two dense N-by-N
  travel-time matrices and the equilibrium solver's intermediate arrays.
- A working MATLAB command must be available at the path configured under
  `project.matlab_command`.

Manual Python installation:

```powershell
python -m pip install -r requirements.txt
```

Development and testing installation:

```powershell
python -m pip install -r requirements-dev.txt
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
4. **Scenarios:** solve the closed- and open-city equilibria and evaluate the
   fixed-distribution accounting benchmark.
5. **Sensitivity:** when requested, re-invert the baseline and rerun all three
   scenarios with productivity and amenity spillovers set to zero.

MATLAB retains explicit damped ARSW-style fixed-point updates. It reports iteration counts and gaps. Reaching an iteration ceiling without meeting tolerance is a hard failure.

For equations, unknown/equation counting, inversion formulas, closures, land-rent accounting and pseudo-code, see the [Codebook](docs/QUETRANSPORT_CODEBOOK.pdf) ([source](docs/QUETRANSPORT_CODEBOOK.tex)).

## Outputs

See the [output showcase](SHOWCASE/) for representative maps and an aggregate
results table from an illustrative application.

| Folder | Contents |
|---|---|
| `outputs/diagnostics/` | resolved configuration, validation and convergence |
| `outputs/inversion/` | inverted fundamentals and baseline objects |
| `outputs/simulation/` | main scenario results, welfare decomposition, and aggregate comparison |
| `outputs/no_spillovers/` | separately inverted and simulated zero-spillover sensitivity results |
| `outputs/tables/` | aggregate outcome tables |
| `outputs/maps/` | transport innovation, imposed shocks and effects |

Local outputs include population, employment, wages, effective wages,
floor-space prices, floor space, output and land rent. Aggregate reports
distinguish expected utility, population, GDP/output, residual land rent, and
three one-way travel-time measures:

- **Immediate commute-time change:** changes the network while retaining the
  original OD probabilities, isolating the network effect before relocation.
- **Post-relocation commute-time change:** uses post-adjustment OD probabilities
  and therefore includes changed residence-workplace matching.
- **Total commuter-minutes change:** multiplies the post-adjustment mean commute
  by commuter population, additionally capturing migration in the open city.

All three are percentage changes in one-way physical travel time relative to
the pre-policy equilibrium—not changes measured in minutes or monetized
benefits. Negative values indicate time savings.

The fixed-distribution output also decomposes worker welfare into commuting,
productivity/wage, and amenity components. Welfare adjusts in the closed city;
outside utility is fixed and population adjusts in the open city. The
fixed-distribution case is an accounting benchmark, not a third market-clearing
equilibrium.

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

Adapted routines from the [ARSW2015 toolkit](https://github.com/Ahlfeldt/ARSW2015-toolkit) are isolated under `src/matlab/functions/arsw/`; see [`vendor/README.md`](vendor/README.md).

## Citation, license and contributing

If you use QUETRANSPORT, please cite **both the toolkit and the ARSW paper that
provides its underlying quantitative urban methodology**.

### Toolkit

> Ahlfeldt, Gabriel M. (2026). *QUETRANSPORT: A Toolkit for Transport Appraisal
> with a Quantitative Urban Model* (Version 0.1.0) [Computer
> software]. https://github.com/Ahlfeldt/QSETRANSPORT-toolkit/tree/main/QUETRANSPORT

### Underlying methodology

> Ahlfeldt, Gabriel M.; Redding, Stephen J.; Sturm, Daniel M.; and Wolf,
> Nikolaus (2015). “The Economics of Density: Evidence from the Berlin Wall.”
> *Econometrica*, 83(6), 2127–2189.
> [https://doi.org/10.3982/ECTA10876](https://doi.org/10.3982/ECTA10876)

Machine-readable metadata for the toolkit and the methodology reference are in
[`CITATION.cff`](CITATION.cff). GitHub can use this file to generate citations
in common formats.

No public software license has yet been selected. Until one is added, all rights are reserved. Selecting a license is required before public release.

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Reports should include the resolved configuration, software versions, failing stage and diagnostics. Never post restricted data publicly.
