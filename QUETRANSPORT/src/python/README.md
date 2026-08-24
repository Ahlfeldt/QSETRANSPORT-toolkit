# Python source

- `run_pipeline.py`: internal cumulative pipeline called by the root master script.
- `common/`: configuration, IDs, progress, validation and scenarios.
- `grid/`: generated-grid, original-polygon and compatibility preparation.
- `ttmatrix/`: matrix construction and user-provided matrix validation.
- `reporting/`: transport, primitive-shock and equilibrium maps.

Normal users run `RUN_QUETRANSPORT.py` and edit the root `project_config.yaml`; they do not run component modules directly. Source code contains no application-specific absolute paths.
