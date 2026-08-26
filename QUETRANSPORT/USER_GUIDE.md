# QUETRANSPORT user guide

A normal application requires three actions: supply spatial files, edit `project_config.yaml`, and run `RUN_QUETRANSPORT.py`.

## 1. Supply source data

### GRID

Place source polygon layers in `input/raw/grid/`. In the configuration, identify population, employment, the developed/retention variable, and optionally one common observed floor-space rent.

Select:

- `square` or `hexagon` to create a new regular model grid; or
- `original` to retain the supplied polygons and ignore `cell_size_km`.

Population and employment are extensive quantities and are allocated by source-area overlap. Rent and the developed indicator are intensive and receive intersection-area-weighted means. Employment is rescaled so its aggregate equals population.

### Travel times

Keep `ttmatrix.source: ttmatrix` to construct matrices.

- Leave both baseline network paths `null` for direct off-network baseline travel.
- Supply both baseline line and station layers when an initial network exists.
- Supply both counterfactual line and station layers for the policy network.

Alternatively, select `user_provided` and configure labeled baseline and counterfactual matrices. In the current TTMATRIX application the user-provided matrix paths correctly remain `null`.

### Optional shocks

For a pure transport experiment, leave `scenario.shocks_shapefile: null`.

Otherwise place a non-overlapping polygon shapefile or GeoPackage in `input/raw/shocks/`. Configure multiplicative fields for productivity, amenities and structural density. Policy polygons may use arbitrary spatial units; GRID area-interpolates them to the model geography. Inspect the generated PDF or PNG imposed-shock maps.

## 2. Edit the root configuration

All normal-user choices are in `project_config.yaml`. Work through sections A–H:

1. project stages and MATLAB command;
2. input and output paths;
3. GRID geography and variables;
4. TTMATRIX assumptions;
5. economic parameters and city closure;
6. numerical controls;
7. optional shocks;
8. reporting.

Keep `project.run_no_spillover_comparison: true` to produce the complete
six-case comparison. The main specification evaluates closed city, open city,
and fixed distribution. The sensitivity specification re-inverts the baseline
and repeats all three after setting both spillover elasticities to zero.

Do not edit generated `input/standardized/runtime_config.json`; it is a run-specific snapshot consumed by MATLAB.

## 3. Run

### Spyder

Open the root `RUN_QUETRANSPORT.py` and run it. The script resolves paths from its own location and streams MATLAB console output back to Spyder.

### PowerShell

```powershell
Set-Location "D:\Dropbox\GA\_research\_TOOLKITS\QUETRANSPORT"
python .\RUN_QUETRANSPORT.py
```

Useful preparation-only command:

```powershell
python .\RUN_QUETRANSPORT.py --prepare-only
```

This is appropriate when MATLAB should run on a faster server. Copy the complete project with standardized inputs to the server, change only the drive prefix if necessary, and run `src/matlab/scripts/run_all.m` in a new MATLAB instance.

## What to inspect

Before interpreting results, inspect:

- `outputs/diagnostics/grid_validation.json`;
- travel-matrix dimensions, IDs and change diagnostics;
- transport-innovation and imposed-shock maps;
- inversion and equilibrium iteration/gap output;
- baseline employment reproduction and accounting checks;
- aggregate tables and closure-specific maps.

The main aggregate table distinguishes three travel-time statistics.
**Immediate commute-time change** holds origin–destination assignments fixed
and isolates the network change. **Post-relocation commute-time change** also
incorporates residence-workplace resorting. **Total commuter-minutes change**
additionally incorporates a change in commuter population. Also inspect
`outputs/simulation/fixed_distribution_welfare_decomposition.csv` and, when
enabled, the separate `outputs/no_spillovers/` results.

If inversion exhausts one 199-iteration inner pass, it restarts from the latest productivity and amenity vectors up to `maximum_inversion_passes`. Failure after the configured pass limit stops the run. Equilibrium non-convergence also stops rather than saving a successful result.

## Common problems

- **Missing package:** allow the master script to install it, or run `python -m pip install -r requirements.txt`.
- **Wrong field name:** copy the exact GIS attribute name into the GRID or scenario configuration.
- **CRS error:** ensure every spatial layer declares its CRS.
- **ID mismatch:** regenerate all standardized files together; never reorder a matrix manually.
- **Out of memory:** use larger cells, original coarser units, or a server with more RAM.
- **Slow network drive:** run preparation or MATLAB from a local/server copy, but preserve the project structure and configuration snapshot.
