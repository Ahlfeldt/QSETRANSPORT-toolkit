# Input data

The Python-only toolkit includes the same raw reference inputs as the mixed
Python–MATLAB toolkit, allowing one-to-one output comparisons. GRID and
TTMATRIX recreate the uncommitted `input/standardized/` files during every
normal run; no MATLAB input is required.

## Bundled reference application

| Input | Location | Role |
|---|---|---|
| `grid_61.*` | `raw/grid/` | Source polygons containing population, employment and a developed-area indicator. |
| `lines.*` | `raw/networks/counterfactual/` | Counterfactual transport lines. |
| `stations.*` | `raw/networks/counterfactual/` | Counterfactual station points. |
| `primitive_changes.*` | `raw/shocks/` | Optional example primitive changes. They are inactive while `scenario.shocks_shapefile` is `null`. |

A shapefile is a set of files, so keep its `.shp`, `.dbf`, `.shx`, `.prj` and
any other sidecar files together. The reference configuration maps `pop_sh` to
population, `emp_sh` to employment and `devle` to the developed/retention
indicator. `pop_sh` and `emp_sh` are spatial shares in this example; GRID
allocates them as extensive quantities and scales aggregate population to the
configured `grid.total_population` of 8,000,000. Employment is subsequently
balanced to the same total.

## Minimum input contract

| Component | Requirement |
|---|---|
| Geography | One or more non-overlapping polygon shapefiles or GeoPackages with a declared CRS. Every layer must contain the configured population, employment and developed fields. An observed common floor-space-rent field is optional. |
| Population and employment | Nonnegative extensive quantities. GRID allocates each source value by the share of its source polygon intersecting a target cell, preserving totals over the covered area. Values may be counts or consistently defined weights/shares when `grid.total_population` supplies the model total. |
| Developed indicator and rent | Intensive variables. GRID calculates intersection-area-weighted target-cell means. A target cell is retained when developed, population or employment is positive. |
| Network construction | A line layer and a station point layer for each supplied network. Both baseline paths must be supplied together or both left `null`; a missing baseline network means direct off-network baseline travel. Both counterfactual paths are required for the policy network. Speeds are configured in km/h. |
| User-provided matrices | Two finite, nonnegative, labelled square CSV matrices. The first column contains row IDs; remaining headers contain column IDs. Row and column ID sets must exactly match GRID's `location_id` values. Both matrices use the same origin–destination orientation and the unit selected by `ttmatrix.time_unit` (`minutes`, `seconds` or `hours`). |
| Optional primitive changes | A non-overlapping polygon shapefile or GeoPackage with multiplicative productivity, amenity and/or structural-density fields. A value of `1` means no change. Set unused mappings—or the entire shock path—to `null`. |

All spatial layers must declare a coordinate reference system. Leave
`grid.analysis_crs` and `ttmatrix.analysis_crs` as `null` to use an appropriate
local projected CRS automatically, or supply a suitable projected EPSG code.

## Starting an application for another city

1. Copy the toolkit so the reference application remains reproducible.
2. Remove the bundled `grid_61` shapefile set from `input/raw/grid/`; GRID reads
   **every** `.shp` and `.gpkg` in that folder. Add only the source polygon
   layers intended for the new application, keeping all shapefile sidecars.
3. Put baseline and counterfactual line/station layers under
   `input/raw/networks/`, or put the two labelled matrices under
   `input/raw/travel_times/`.
4. Add optional policy polygons under `input/raw/shocks/`.
5. Edit `project_config.yaml`: update all paths, exact source-field names, grid
   geometry and size, population total, travel speeds/units and optional shock
   mappings. Select `ttmatrix.source: ttmatrix` or `user_provided`.
6. Run `RUN_QUETRANSPORT.py`. Do not hand-edit or mix previously generated
   standardized files; GRID and TTMATRIX validate and recreate them together.
7. Inspect `outputs/diagnostics/grid_validation.json`,
   `outputs/diagnostics/travel_time_validation.json` and the validation maps
   before interpreting the economic results.

See the fully commented [`project_config.yaml`](../project_config.yaml) and the
mixed toolkit's detailed [user guide](../../QUETRANSPORT/USER_GUIDE.md) and
[standardized data contract](../../QUETRANSPORT/docs/DATA_CONTRACT.md). The raw
input and standardized-data contracts are identical in both versions.

## Ready-made city grids

Ready-made population and employment grids for many cities can be downloaded
from the [AABPL toolkit](https://github.com/Ahlfeldt/AABPL-toolkit). Convenient
map-illustrated dropdown menus provide downloads for
[381 US metropolitan areas](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-381-us-msas?authuser=0)
and
[125 global cities](https://sites.google.com/view/ahlfeldt/toolkits-and-webtools/prime-locations/prime-locations-in-125-global-cities?authuser=0).

To reproduce a controlled solver-only comparison instead, populate
`input/standardized/` with the same data contract used by QUETRANSPORT and run
with `config/project_config.identical_standardized_inputs.yaml`.
