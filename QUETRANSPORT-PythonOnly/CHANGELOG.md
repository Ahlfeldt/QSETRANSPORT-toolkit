# Changelog

## 0.1.3 — 2026-11-07

- Made standalone TTMATRIX graph construction and Dijkstra routing the default.
- Retained the previous travel constructor as `legacy_access_network_egress`
  and added disconnected-component and detour diagnostics.

## 0.1.2 — 2026-11-07

- Replaced exhaustive station-pair matrix construction with parallel
  TTMATRIX-style origin routing.
- Retained exact all-stations routing as the default and added an explicit
  nearest-station approximation for very large applications.
- Added and validated the browser webtool distribution.

## 0.1.1 — 2026-08-27

- Added network-safe GeoPackage publication for Windows SMB and Linux NFS
  project drives, without creating persistent toolkit copies.
- Validated complete mixed and Python-only runs on a Windows server, Linux
  server, and Windows desktop; economic outputs remain unchanged.

## 0.1.0 — 2026-08-24

- Initial beta release.
