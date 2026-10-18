# Generic 2D and 3D packed-tree comparison

Measured 18 October 2026: candidate production source `04028ea` against unchanged source `3d2d88f` (library behavior from NuGet 1.0.8). The current implementation uses Hilbert keys in 2D and three-axis Morton keys in 3D, primitive radix sorting, bottom-up packing, compact mutable nodes, and bulk copying of contained leaves. Plain, snapshot, and concurrent APIs share these implementations. Typed bounds and exact integer selection/split metrics remain intact.

All measured build and aggregate-query medians improved. At 100,000 entries, 3D construction improved 4.73–5.56× and aggregate queries 1.80–3.80× across the four types and two distributions. Mutability remains direct, with a performance tradeoff: some 10,000-entry clustered move batches were up to 52.1% slower, and 100k uniform 3D moves up to 13.6% slower. All post-move aggregate queries improved. The adoption prioritizes bulk construction and search; it does not claim universally faster updates.

## Plain mutable APIs

Median of three fresh-process block averages; lower is faster. Query figures are the median of the within-process sums of four separately measured groups of 16 windows. All returned IDs are materialized and consumed. Each row compares identical coordinate/dimension/fixture/API regimes.

| API | Coordinates | Entries | Distribution | Old build ms | New build ms | Build speedup | Old 64 queries µs | New 64 queries µs | Query speedup |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| 2D | int | 10,000 | uniform | 2.812 | 0.586 | 4.80× | 212.73 | 77.63 | 2.74× |
| 2D | int | 10,000 | clustered | 2.616 | 0.618 | 4.23× | 232.82 | 74.35 | 3.13× |
| 2D | int | 100,000 | uniform | 38.147 | 7.729 | 4.94× | 2047.45 | 698.25 | 2.93× |
| 2D | int | 100,000 | clustered | 40.082 | 8.052 | 4.98× | 2233.78 | 693.95 | 3.22× |
| 2D | long | 10,000 | uniform | 5.480 | 0.649 | 8.44× | 211.86 | 84.04 | 2.52× |
| 2D | long | 10,000 | clustered | 5.501 | 0.652 | 8.44× | 234.82 | 75.69 | 3.10× |
| 2D | long | 100,000 | uniform | 36.169 | 8.718 | 4.15× | 2040.45 | 756.95 | 2.70× |
| 2D | long | 100,000 | clustered | 35.210 | 8.570 | 4.11× | 2219.45 | 732.28 | 3.03× |
| 2D | float | 10,000 | uniform | 2.030 | 0.587 | 3.46× | 222.99 | 82.61 | 2.70× |
| 2D | float | 10,000 | clustered | 1.980 | 0.601 | 3.30× | 247.83 | 74.82 | 3.31× |
| 2D | float | 100,000 | uniform | 29.418 | 7.621 | 3.86× | 2115.93 | 729.77 | 2.90× |
| 2D | float | 100,000 | clustered | 27.142 | 7.881 | 3.44× | 2257.00 | 695.49 | 3.25× |
| 2D | double | 10,000 | uniform | 3.660 | 0.664 | 5.52× | 234.92 | 83.32 | 2.82× |
| 2D | double | 10,000 | clustered | 3.636 | 0.661 | 5.50× | 261.39 | 74.23 | 3.52× |
| 2D | double | 100,000 | uniform | 32.554 | 8.302 | 3.92× | 2142.37 | 764.07 | 2.80× |
| 2D | double | 100,000 | clustered | 29.256 | 8.483 | 3.45× | 2317.73 | 729.49 | 3.18× |
| 3D | int | 10,000 | uniform | 5.643 | 0.761 | 7.42× | 184.46 | 93.41 | 1.97× |
| 3D | int | 10,000 | clustered | 5.506 | 0.748 | 7.36× | 216.18 | 62.56 | 3.46× |
| 3D | int | 100,000 | uniform | 49.436 | 10.116 | 4.89× | 1155.61 | 567.90 | 2.03× |
| 3D | int | 100,000 | clustered | 47.048 | 9.941 | 4.73× | 1136.74 | 321.46 | 3.54× |
| 3D | long | 10,000 | uniform | 7.693 | 0.888 | 8.66× | 197.59 | 100.76 | 1.96× |
| 3D | long | 10,000 | clustered | 7.775 | 0.876 | 8.88× | 227.32 | 63.15 | 3.60× |
| 3D | long | 100,000 | uniform | 55.450 | 9.978 | 5.56× | 1222.57 | 597.25 | 2.05× |
| 3D | long | 100,000 | clustered | 49.573 | 9.949 | 4.98× | 1214.81 | 320.70 | 3.79× |
| 3D | float | 10,000 | uniform | 2.920 | 0.684 | 4.27× | 203.45 | 102.50 | 1.98× |
| 3D | float | 10,000 | clustered | 2.829 | 0.660 | 4.29× | 237.83 | 63.87 | 3.72× |
| 3D | float | 100,000 | uniform | 39.273 | 8.306 | 4.73× | 1208.98 | 661.02 | 1.83× |
| 3D | float | 100,000 | clustered | 39.546 | 8.262 | 4.79× | 1166.79 | 321.92 | 3.62× |
| 3D | double | 10,000 | uniform | 4.238 | 0.779 | 5.44× | 197.77 | 108.25 | 1.83× |
| 3D | double | 10,000 | clustered | 4.220 | 0.775 | 5.45× | 232.80 | 64.31 | 3.62× |
| 3D | double | 100,000 | uniform | 43.196 | 9.087 | 4.75× | 1255.57 | 695.62 | 1.80× |
| 3D | double | 100,000 | clustered | 45.058 | 8.899 | 5.06× | 1228.04 | 323.27 | 3.80× |

## Snapshot and concurrent APIs

10,000 uniform entries. Snapshot construction includes `ReplaceAll`; concurrent construction includes `BulkLoad` and disposal. These wrapper measurements include their normal publication/locking work. Snapshots replace complete batches rather than moving individual entries.

| API | Coordinates | Update model | Old build ms | New build ms | Old 64 queries µs | New 64 queries µs |
|---|---|---|---:|---:|---:|---:|
| 2D | int | snapshot | 2.792 | 0.605 | 210.76 | 77.60 |
| 2D | int | concurrent | 5.456 | 0.970 | 214.84 | 80.70 |
| 2D | long | snapshot | 5.480 | 0.662 | 216.05 | 81.59 |
| 2D | long | concurrent | 3.885 | 1.581 | 216.50 | 82.07 |
| 2D | float | snapshot | 2.032 | 0.592 | 223.09 | 82.35 |
| 2D | float | concurrent | 3.848 | 0.975 | 225.51 | 84.45 |
| 2D | double | snapshot | 3.658 | 0.633 | 228.08 | 83.91 |
| 2D | double | concurrent | 3.139 | 1.563 | 225.47 | 85.60 |
| 3D | int | snapshot | 5.286 | 0.762 | 185.43 | 92.99 |
| 3D | int | concurrent | 7.781 | 1.267 | 188.54 | 98.38 |
| 3D | long | snapshot | 7.800 | 0.868 | 198.94 | 102.73 |
| 3D | long | concurrent | 6.269 | 2.197 | 198.76 | 104.73 |
| 3D | float | snapshot | 2.892 | 0.683 | 195.92 | 107.10 |
| 3D | float | concurrent | 4.994 | 1.263 | 200.88 | 104.48 |
| 3D | double | snapshot | 4.224 | 0.817 | 200.31 | 103.97 |
| 3D | double | concurrent | 3.875 | 2.204 | 202.60 | 109.33 |

## Mutation guardrails

Plain trees: move the first 1,000 entries through the public API, with 64 moves on a separate tree warming the code beforehand. Mutation batches are timed once per process, so their ranges and inference differ from calibrated query/build throughput; unvisited paths can still incur first-use work. Exact result sets are checked again afterward. Tree grouping changes split/condensation work; this harness does not isolate the cause of the observed regressions. Concurrent move-batch data is also retained in the complete CSV.

| API | Coordinates | Entries | Distribution | Old moves ms | New moves ms | Old post-move queries µs | New post-move queries µs |
|---|---|---:|---|---:|---:|---:|---:|
| 2D | int | 10,000 | uniform | 27.055 | 31.239 | 273.63 | 96.01 |
| 2D | int | 10,000 | clustered | 23.785 | 28.331 | 301.26 | 94.63 |
| 2D | int | 100,000 | uniform | 82.534 | 96.122 | 2538.64 | 992.31 |
| 2D | int | 100,000 | clustered | 68.032 | 41.803 | 2591.96 | 865.76 |
| 2D | long | 10,000 | uniform | 31.510 | 36.317 | 279.83 | 113.47 |
| 2D | long | 10,000 | clustered | 27.988 | 33.600 | 313.58 | 93.33 |
| 2D | long | 100,000 | uniform | 95.057 | 110.323 | 2698.54 | 1189.56 |
| 2D | long | 100,000 | clustered | 74.274 | 46.156 | 2591.67 | 926.79 |
| 2D | float | 10,000 | uniform | 7.531 | 8.050 | 266.52 | 103.78 |
| 2D | float | 10,000 | clustered | 6.114 | 8.001 | 320.85 | 89.92 |
| 2D | float | 100,000 | uniform | 19.706 | 26.103 | 2535.97 | 1072.83 |
| 2D | float | 100,000 | clustered | 16.209 | 13.247 | 2651.37 | 886.62 |
| 2D | double | 10,000 | uniform | 7.499 | 8.800 | 308.21 | 105.26 |
| 2D | double | 10,000 | clustered | 6.144 | 7.561 | 331.82 | 92.94 |
| 2D | double | 100,000 | uniform | 24.787 | 25.285 | 2707.73 | 1083.01 |
| 2D | double | 100,000 | clustered | 22.106 | 12.928 | 2942.87 | 916.42 |
| 3D | int | 10,000 | uniform | 34.779 | 36.344 | 238.45 | 111.61 |
| 3D | int | 10,000 | clustered | 26.891 | 40.892 | 279.01 | 76.43 |
| 3D | int | 100,000 | uniform | 80.877 | 86.948 | 1343.56 | 765.01 |
| 3D | int | 100,000 | clustered | 89.169 | 54.268 | 1335.92 | 390.58 |
| 3D | long | 10,000 | uniform | 34.942 | 37.446 | 244.94 | 122.91 |
| 3D | long | 10,000 | clustered | 27.321 | 41.513 | 291.52 | 78.75 |
| 3D | long | 100,000 | uniform | 81.202 | 88.311 | 1419.74 | 789.36 |
| 3D | long | 100,000 | clustered | 90.615 | 53.157 | 1464.38 | 399.90 |
| 3D | float | 10,000 | uniform | 9.180 | 9.265 | 250.94 | 114.36 |
| 3D | float | 10,000 | clustered | 7.777 | 11.430 | 302.47 | 76.28 |
| 3D | float | 100,000 | uniform | 18.759 | 21.313 | 1404.02 | 844.32 |
| 3D | float | 100,000 | clustered | 21.223 | 16.857 | 1375.74 | 390.67 |
| 3D | double | 10,000 | uniform | 9.180 | 9.823 | 262.10 | 125.76 |
| 3D | double | 10,000 | clustered | 7.650 | 11.418 | 304.72 | 80.31 |
| 3D | double | 100,000 | uniform | 20.071 | 22.650 | 1500.03 | 898.46 |
| 3D | double | 100,000 | clustered | 21.984 | 16.280 | 1504.97 | 399.97 |

## Method, evidence and limits

Ryzen 9 5950X, Windows 11 build 26200, .NET SDK 10.0.402/runtime 10.0.13, Release x64 managed code. CPU affinity mask 4, tiering disabled, serial workers under `Global\Tedd.RTree.PerformanceHost`. Three matched fresh-process blocks; fixed shuffled order and seed 47381; 100 ms calibration followed by one measured block. All 288 scheduled processes validate exact IDs before timing; mutable APIs additionally validate after movement. No observer is active during timing. Background desktop activity is uncontrolled; fresh PIDs are not proof of independent samples. No tail-latency or significance claims.

The new fixture is explicitly 2D or 3D, with seed 73211, integer-valued coordinates represented exactly in all four types, and widths 0/20/200/1000. It includes nonempty points, edge contacts, and full containment. Geometry/adapters are prepared outside timing; index construction includes a small identical harness adapter in both arms. Build allocations measure the current managed thread, not live memory or process working set. Query timings include result consumption and interface adapter dispatch.

Correctness includes mixed insert/remove/update, duplicate bounds/reference values, capacities 4/5/16/128, root collapse, empty/singleton/radix-size cases, signed/extreme coordinates, isolated subnormal extents, adjacent long values beyond 2^53, a z-only long dataset, indexed-only sources, source-order preservation, append/count semantics, cross-type/dimension workspace reuse, and wrapper batch/concurrency contracts. Search comparisons never use quantized keys. Reusable workspace primitive buffers require 12 bytes per reserved entry, excluding array/object headers.

The 3D exploration compared both Hilbert and Morton ordering with unchanged controls. Morton was retained for substantially faster construction; Hilbert had faster uniform queries. This choice does not establish a universal best ordering. Rust competitors from the earlier comparison implement 2D indexing; their timings are not reused as 3D competitors. The original unsuffixed 2D implementation retains its separate historical comparison.

DotNetLab diagnostic captures and optimized JIT listings are separate from confirmation workers. These changed-dependency external targets use the ordinary diagnostic lane; no qualified native promotion is claimed. The ledger preserves candidate decisions, contradictory observations, and diagnostic IDs in the [research record](../Research/2026-10-18-generic-packed/REPORT.md).

Raw [samples](results/generic-packed/confirmation/samples.json), [launch records](results/generic-packed/confirmation/processes.json), [frozen protocol and binary hashes](results/generic-packed/confirmation/protocol.json), and [complete medians, ranges and allocations](results/generic-packed/confirmation/summary.csv) are retained. Exploration results are in adjacent `ordering`, `transfer`, and `inline` directories. Reproduce with `generic-packed/locked.ps1` after staging the original control library in a designated workspace, then `generic-packed/summarize.py`.
