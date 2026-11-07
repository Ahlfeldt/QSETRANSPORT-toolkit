# QUETRANSPORT browser interface

This directory is an additive browser adapter for the Python-only toolkit. It
does not replace or modify the existing command-line workflow.

The application is designed for static hosting on GitHub Pages and embedding
in Google Sites. Pyodide runs the existing numerical model in a Web Worker.
Browser controls replace the user choices normally supplied through
`project_config.yaml`.

## Development

Run `START_WEBTOOL.py`, then open the address it prints:

```text
http://localhost:8765/webtool/
```

Keep the server window open while using the application. Pyodide and browser
workers cannot run directly from a `file://` URL. The equivalent manual command,
run from the repository root, is:

```text
python -m http.server 8000
```

The first release targets the 125 AABPL global cities, square or hexagonal
analysis grids, a limit of 2,000 retained cells on desktop and 1,000 in the mobile layout, direct off-network baseline
travel, user-drawn counterfactual lines with optional stations, and polygon
shocks to productivity, amenities, and structural density.

Travel times use the same TTMATRIX-style origin-routing principle as the
desktop toolkit. The browser keeps the exact all-stations choice because its
cell limit makes this tractable, and it always retains direct off-network
travel as an alternative.
