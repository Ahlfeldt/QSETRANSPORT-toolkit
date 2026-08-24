# QSETRANSPORT

**A platform for deploying user-friendly transport simulation toolkits.**

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

1. **Supply urban data** for the study area.
2. **Describe the baseline and improved transport system.**
3. **Choose model assumptions and policy scenarios in one configuration file.**
4. **Run the pipeline and inspect validated tables, diagnostics, and maps.**

Depending on the deployed toolkit, users can work with original spatial units
or regular square and hexagonal grids. The platform is compatible with gridded
datasets available for many cities through the AABPL toolkit, while its
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

The first available deployable toolkit,
[`QUETRANSPORT`](QUETRANSPORT/), evaluates transport improvements in a
quantitative urban model with spatial equilibrium. It is one toolkit within the
broader QSETRANSPORT collection. It:

- prepares consistent model geography and variables;
- constructs or validates baseline and counterfactual travel-time matrices;
- recovers a model-consistent baseline spatial economy;
- simulates open- and closed-city counterfactuals;
- supports additional productivity, amenity, and density changes; and
- produces diagnostics, local and aggregate results, and maps.

The economic core builds on the structure and numerical approach of Ahlfeldt,
Redding, Sturm and Wolf (2015), generalized beyond Berlin-specific inputs and
dimensions. See the [QUETRANSPORT documentation](QUETRANSPORT/README.md) for the
model, inputs, installation instructions, examples, and complete workflow.

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

Requirements depend on the toolkit being deployed. The currently available
QUETRANSPORT toolkit requires:

- **Python 3** for configuration, geospatial data preparation, travel-time
  construction, validation, and mapping;
- the Python scientific and geospatial stack listed in
  [`QUETRANSPORT/requirements.txt`](QUETRANSPORT/requirements.txt), including
  NumPy, pandas, GeoPandas, Pyogrio, Shapely, Matplotlib, SciPy, NetworkX, and
  PyYAML; and
- **MATLAB** for baseline inversion and spatial-equilibrium simulations.

The current MATLAB implementation uses base MATLAB functionality. The Mapping,
Optimization, Global Optimization, and Statistics and Machine Learning
Toolboxes are not required by the present QUETRANSPORT code. Geospatial
operations and map production are performed in Python.

See the [QUETRANSPORT requirements](QUETRANSPORT/README.md#requirements) for
installation commands and version guidance. Future toolkits may have different
software requirements, which will be documented in their own subfolders.

## See what QUETRANSPORT produces

The [QUETRANSPORT showcase](QUETRANSPORT/SHOWCASE/) presents representative
closed- and open-city maps together with an aggregate results table from one
illustrative transport scenario. It demonstrates how the toolkit communicates
spatial changes in population, wages, and output while distinguishing welfare
and migration responses across city closures.

## Explore the available toolkit

- [Open QUETRANSPORT](QUETRANSPORT/)
- [View the output showcase](QUETRANSPORT/SHOWCASE/)
- [Read the user guide](QUETRANSPORT/USER_GUIDE.md)
- [Review the model codebook](QUETRANSPORT/docs/QUETRANSPORT_CODEBOOK.pdf)
- [Check implementation status](QUETRANSPORT/STATUS.md)
- [Contribute](QUETRANSPORT/CONTRIBUTING.md)

## Research foundation

Ahlfeldt, G. M., Redding, S. J., Sturm, D. M., and Wolf, N. (2015), “The
Economics of Density: Evidence from the Berlin Wall,” *Econometrica*, 83(6),
2127–2189.
