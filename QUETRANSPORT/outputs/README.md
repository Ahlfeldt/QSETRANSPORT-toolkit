# Generated outputs

Running QUETRANSPORT creates this output structure:

```text
outputs/
├── diagnostics/
├── inversion/
├── maps/
├── simulation/
├── tables/
└── no_spillovers/
    ├── inversion/
    └── simulation/
```

Generated outputs are deliberately not committed. A complete run can exceed
1.5 GB, primarily because MATLAB solver-state files contain dense commuting
objects. All outputs are reproducible from the bundled raw inputs.

See the [output showcase](../SHOWCASE/) for representative maps, aggregate
results, and explanations of the reported measures.
