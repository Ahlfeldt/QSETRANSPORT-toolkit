# Generated outputs

Running QUETRANSPORT-PythonOnly creates this output structure:

```text
outputs/
├── diagnostics/
├── inversion/
├── maps/
└── simulation/
```

Generated outputs are deliberately not committed. A complete run can exceed
600 MB because serialized solver states contain dense commuting objects. All
outputs are reproducible from the bundled raw inputs.

The mixed toolkit's [output showcase](../../QUETRANSPORT/SHOWCASE/) presents the
same core maps and aggregate measures produced by this implementation.
