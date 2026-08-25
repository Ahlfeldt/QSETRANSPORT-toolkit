# QSETRANSPORT

**A platform for deploying user-friendly transport simulation toolkits.**

**Version 0.1.0 (beta)** · **Author: [Gabriel M. Ahlfeldt](https://www.ahlfeldt.com/)**

QSETRANSPORT is an open, modular platform for studying how transport
improvements reshape cities and regions. It provides a common home for multiple
deployable toolkits that connect spatial data and transport scenarios to
economic and spatial models through transparent, reproducible workflows.

The ambition is simple: make sophisticated place-based policy analysis usable
beyond the small group of researchers who develop the underlying models. Each
toolkit packages a particular modeling approach into an accessible application,
while shared conventions make data and scenarios reusable across toolkits.

## What can QSETRANSPORT evaluate?

A deployed QSETRANSPORT toolkit compares a baseline transport system with a
proposed improvement and traces its effects through the modeled city or region.
Depending on the toolkit and selected model, outcomes can include:

- travel times and accessibility;
- the location of residents and employment;
- wages, productivity, amenities, and rents;
- economic activity and land use;
- aggregate welfare or city population; and
- maps showing where gains and adjustments occur.

Transport interventions can be combined with other changes in economic
fundamentals, allowing users to evaluate broader policy packages rather than an
isolated infrastructure change.

## Designed for real cities—and for users

Each toolkit is designed around a straightforward workflow:

1. **Download a ready-made city grid** from the
   [AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit), or supply your
   own urban data.
2. **Describe the baseline and improved transport system.**
3. **Choose model assumptions and policy scenarios in one configuration file.**
4. **Run the pipeline and inspect validated tables, diagnostics, and maps.**

Depending on the deployed toolkit, users can work with original spatial units
or regular square and hexagonal grids. The platform is compatible with
downloadable population and employment grids for **381 US metropolitan areas**
and **125 global cities** from the
[AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit). This provides a
direct route from selecting a city to configuring a transport scenario, while
standardized interfaces also allow other data sources and transport matrices to
be used.

## A collection of deployable toolkits

QSETRANSPORT is the umbrella platform—not a single model application. Individual
subfolders contain toolkits that can be configured and deployed for particular
cities, transport interventions, and research questions. A deployment may use
one toolkit or, where appropriate, combine several compatible toolkits.

New toolkits can introduce different model families and outcome concepts while
reusing common inputs, scenario definitions, validation rules, and reporting
conventions. This modular structure allows the collection to grow without
forcing every application into one economic model.

### Quantitative urban models

The first available deployable toolkit evaluates transport improvements in a
quantitative urban model with spatial equilibrium. It is available in two
closely aligned implementations:

- [`QUETRANSPORT`](QUETRANSPORT/) uses Python for data preparation, travel
  matrices, validation, and mapping, and MATLAB for inversion and equilibrium
  simulation. Its MATLAB scripts and functions remain close to the structure
  and conventions of the
  [ARSW2015 toolkit](https://github.com/Ahlfeldt/ARSW2015-toolkit). They will
  therefore be familiar to existing ARSW2015 users, making the model easier to
  understand, adapt, and extend.
- [`QUETRANSPORT-PythonOnly`](QUETRANSPORT-PythonOnly/) implements the complete
  workflow—including inversion and equilibrium simulation—in Python and
  requires no MATLAB installation.

Both implementations:

- prepare consistent model geography and variables;
- construct or validate baseline and counterfactual travel-time matrices;
- recover a model-consistent baseline spatial economy;
- simulate open- and closed-city counterfactuals;
- evaluate a fixed-distribution benchmark for baseline commuters;
- compare results with and without endogenous productivity and amenity
  spillovers;
- support additional productivity, amenity, and density changes; and
- produce diagnostics, local and aggregate results, and maps.

The economic core builds on the structure and numerical approach of Ahlfeldt,
Redding, Sturm and Wolf (2015), generalized beyond Berlin-specific inputs and
dimensions. The Python-only implementation has been validated against the
mixed Python–MATLAB implementation using identical raw and standardized inputs;
aggregate and location-level results agree closely. See the
[QUETRANSPORT documentation](QUETRANSPORT/README.md) or the
[Python-only documentation](QUETRANSPORT-PythonOnly/README.md) for installation
and workflow guidance.

Additional deployable toolkits and model families are planned.

## Built on established research toolkits

QSETRANSPORT brings together and extends ideas and components from existing
research software, including:

- the [**ARSW2015 toolkit**](https://github.com/Ahlfeldt/ARSW2015-toolkit)
  for quantitative urban equilibrium;
- the [**GRID toolkit**](https://github.com/Ahlfeldt/GRID-toolkit) for
  constructing consistent spatial data; and
- the [**TTMATRIX toolkit**](https://github.com/Ahlfeldt/TTMATRIX-toolkit) for
  representing transport accessibility.

The project uses explicit data contracts between these components so that each
stage can be inspected, tested, or replaced independently.

## Project status

QSETRANSPORT is research software under active development. The quantitative
urban-model implementation is available as a beta version; additional testing,
examples, documentation, and model families are in development.

Results should always be interpreted alongside the selected assumptions, input
validation, and numerical convergence diagnostics.

## Software requirements

Requirements depend on the implementation selected. Both QUETRANSPORT variants
require:

- **Python 3** for configuration, geospatial data preparation, travel-time
  construction, validation, and mapping;
- the Python scientific and geospatial stack listed in
  [`QUETRANSPORT/requirements.txt`](QUETRANSPORT/requirements.txt), including
  NumPy, pandas, GeoPandas, Pyogrio, Shapely, Matplotlib, SciPy, NetworkX, and
  PyYAML.

The mixed [`QUETRANSPORT`](QUETRANSPORT/) implementation additionally requires
**MATLAB** for baseline inversion and spatial-equilibrium simulations. The
[`QUETRANSPORT-PythonOnly`](QUETRANSPORT-PythonOnly/) implementation performs
those stages in NumPy/SciPy and requires **no MATLAB installation**.

The current MATLAB implementation uses base MATLAB functionality. The Mapping,
Optimization, Global Optimization, and Statistics and Machine Learning
Toolboxes are not required by the present QUETRANSPORT code. Geospatial
operations and map production are performed in Python.

See the [QUETRANSPORT requirements](QUETRANSPORT/README.md#requirements) or
[Python-only requirements](QUETRANSPORT-PythonOnly/README.md#requirements) for
installation guidance. Future toolkits may have different requirements, which
will be documented in their own subfolders.

## See what QUETRANSPORT produces

The [QUETRANSPORT showcase](QUETRANSPORT/SHOWCASE/) presents representative
maps together with an aggregate comparison of closed-city, open-city, and
fixed-distribution scenarios—with and without endogenous spillovers. It also
shows how immediate network travel-time effects differ from post-relocation
mean commutes and aggregate commuter-minutes.

## Explore the available toolkit

- [Open QUETRANSPORT](QUETRANSPORT/)
- [Open QUETRANSPORT-PythonOnly](QUETRANSPORT-PythonOnly/)
- [View the output showcase](QUETRANSPORT/SHOWCASE/)
- [Read the user guide](QUETRANSPORT/USER_GUIDE.md)
- [Review the model codebook](QUETRANSPORT/docs/QUETRANSPORT_CODEBOOK.pdf)
- [Check implementation status](QUETRANSPORT/STATUS.md)
- [Contribute](QUETRANSPORT/CONTRIBUTING.md)

## Research foundation

Ahlfeldt, G. M., Redding, S. J., Sturm, D. M., and Wolf, N. (2015), “The
Economics of Density: Evidence from the Berlin Wall,” *Econometrica*, 83(6),
2127–2189.

## Citation

If you use QSETRANSPORT in research, teaching, or applied policy work, please
cite the platform as:

> Ahlfeldt, Gabriel M. (2026). *QSETRANSPORT: A Platform for User-Friendly
> Transport Simulation Toolkits* (Version 0.1.0) [Computer software].
> https://github.com/Ahlfeldt/QSETRANSPORT-toolkit

Machine-readable citation metadata are provided in [`CITATION.cff`](CITATION.cff),
which GitHub can use to generate citations in common formats. When using an
individual toolkit, please also follow the toolkit-specific citation guidance;
QUETRANSPORT, for example, requires citation of both the software and its
underlying ARSW methodology.
