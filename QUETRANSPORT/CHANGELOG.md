# Changelog

## 0.1.3 — 2026-11-07

- Made the standalone TTMATRIX augmented-graph methodology the default travel
  constructor, with its walking links, station connectors and Dijkstra routing.
- Retained the previous access--network--egress method as an explicit legacy
  option and added disconnected-component and detour diagnostics.

## 0.1.2 — 2026-11-07

- Replaced exhaustive station-pair matrix construction with parallel
  TTMATRIX-style origin routing.
- Retained exact all-stations routing as the default and added an explicit
  nearest-station approximation for very large applications.
- Verified exact travel matrices and economically unchanged model outputs.

## 0.1.1 — 2026-08-27

- Added network-safe GeoPackage publication for Windows SMB and Linux NFS
  project drives, without creating persistent toolkit copies.
- Validated complete mixed and Python-only runs on a Windows server, Linux
  server, and Windows desktop; economic outputs remain unchanged.

## 0.1.0 — 2026-08-24

- Initial beta release.
