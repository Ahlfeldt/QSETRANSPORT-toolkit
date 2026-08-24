# Optional configuration templates

The active, normal-user configuration is `../project_config.yaml`, placed beside
`RUN_QUETRANSPORT.py` in the project root so both first-order user files are
immediately visible.

This `config` subfolder contains only optional templates and preserved examples:

- `project_config.raw_mrrh2018.yaml`: named copy of the raw-input example;
- `project_config.example.yaml`: generic template;
- `project_config.precomputed_mrrh2018.yaml`: compatibility mode using existing outputs.

A normal user edits only the root `project_config.yaml`. Its sections cover raw
inputs, GRID, TTMATRIX, economic parameters, numerical controls, shocks, and
reporting. Python validates it and writes
`input/standardized/runtime_config.json`, which MATLAB reads. The generated JSON
must not be edited manually.

Advanced users may run the internal pipeline with another template by passing
`--config PATH`, but the root master script requires no path selection.