# TTMATRIX routing methods

QUETRANSPORT supports two travel-time constructors. Select one with
`ttmatrix.routing_method`. This choice changes only travel-time construction;
the standardized matrix contract and downstream economic model are unchanged.

## `standalone_ttmatrix` (default)

This method reproduces the public standalone TTMATRIX graph methodology:

1. project locations, stations and network lines into a metric CRS;
2. snap network-segment endpoints within `snap_tolerance_m` to their cluster
   centroid;
3. split network lines using the buffered station rule;
4. retain every network-line coordinate as a graph vertex and weight network
   edges by network travel time;
5. connect every station to its nearest network vertex with
   `station_connector_minutes`;
6. connect every location to its `point_station_neighbors` nearest stations at
   the walking speed;
7. add the union of every location's `point_walking_neighbors` nearest-location
   walking links; and
8. run weighted NetworkX Dijkstra from every location.

The standalone script assumes a supplied network. QUETRANSPORT's documented
null-network baseline is implemented as the same nearest-neighbour walking
graph without station or network edges. A null counterfactual continues to copy
the complete baseline matrix.

The default `workers: 1` matches standalone TTMATRIX. `workers: auto` uses up
to eight spawned processes. Multiple processes can help larger graphs but also
duplicate interpreter and graph memory; they should be benchmarked on the
machine used for production.

## `direct_station_access`

This is the descriptive name for the routing method used by earlier toolkit
versions. Existing configurations that use `legacy_access_network_egress`
remain valid as a backward-compatible alias.

This option retains the earlier QUETRANSPORT method. Straight-line direct
travel is available for every OD pair. Network alternatives combine
straight-line access to candidate stations, shortest travel within the network,
and straight-line egress. `legacy_station_candidates: all` permits every
station; a positive integer restricts the candidate set.

The legacy method does not use the sparse location-neighbour walking graph.
The two methods therefore encode different walking and station-access choices
and are not numerically equivalent.

## Shared matrix contract

Both methods preserve the standardized `location_id` row and column ordering,
write minutes, and apply `intrazonal_rule` only after routing. Selecting
`ttmatrix.source: user_provided` bypasses both constructors and retains the
existing matrix validation path.

## Disconnections and detours

A fixed-neighbour walking graph can be disconnected. With the default
`unreachable_rule: stop`, any non-finite OD time stops the pipeline. Increasing
`point_walking_neighbors` is an explicit user decision; the toolkit does not
silently add links.

Even a connected sparse graph can generate long walking detours relative to a
straight line. Diagnostics record walking-component counts, unreachable pairs,
the 99th-percentile and maximum detour ratios, and the number exceeding
`detour_warning_ratio`. They report the methodology's limitation without
changing its graph.

## Validation and current-application benchmark

An independent test transcription of unchanged standalone TTMATRIX was run on
identical synthetic points, stations and network lines. Graph routing matrices
agree to an absolute tolerance of `1e-12`. End-to-end tests also verify location
ordering, minute units, finite values, and the configured within-location time.

The existing 3,577-location toolkit application was benchmarked on 7 November
2026 from temporary copies of its standardized IDs and centroids; package data
and outputs were not modified. Peak memory is the sampled resident memory of
the complete process tree. Times include matrix construction and CSV export.

| Method | Baseline routing | Counterfactual routing | Total matrix stage | Peak memory |
|---|---:|---:|---:|---:|
| `standalone_ttmatrix`, 1 worker | 16.18 s | 32.35 s | 63.75 s | 1,219 MB |
| `direct_station_access`, 1 worker | 0.01 s | 2.26 s | 17.48 s | 1,026 MB |

For the standalone method, the existing application produced one connected
walking component, zero unreachable pairs, a counterfactual 99th-percentile
detour ratio of 1.155, and a maximum ratio of 2.0. The optimized legacy method
is faster at this application size; the standalone method is nevertheless the
default because it implements the requested TTMATRIX graph assumptions and has
a fixed-neighbour sparse graph rather than unrestricted location--station
access. Performance should be re-benchmarked for the intended grid and machine.
