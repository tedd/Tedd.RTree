# C# libraries in the shared 2D comparison

Measured 18 October 2026. All five C# chart scores use this complete fresh 180-process record. The three Rust scores retain the separate same-day [optimized direct/interop record](MUTABLE-PACKED.md). Geometry, runtime and timing settings match; sessions were not interleaved. No rescaling or selection between old/new Tedd timings is performed. Small differences need further measurement.

## APIs and construction

| Library | Version | Construction / query API |
|---|---|---|
| Tedd.RTree | Source af521db (NuGet 1.0.14 code) | BulkLoad; reused result list |
| RBush | 4.0.0 | BulkLoad; Search collection |
| NTS STRtree | 2.6.0 | Insert batch + Build; better median of Query list / reusable IItemVisitor |
| RTree | 1.1.0 | Incremental Add; Intersects collection; exact float z=0 embedding |
| Enyim RTree | 1.0.5 | Load with fresh working list; Search collection; published binary |

NTS does not accept inserts after construction. Enyim targets .NET Framework and its published binary disables optimizations; NU1701 is expected. The runtime checks establish tested behavior on .NET 10, not general compatibility. SharpTrees 1.0.6 remains excluded for an existing exact-ID correctness failure. Benchmark packages are not dependencies of the shipped library. Official core paths and package build hooks were inspected before execution; [provenance](../Research/2026-10-18-csharp-charts/provenance.json) records package/source hashes and limitations.

## Chart measurements

| Entries | Distribution | Library | Build ms | Mode | 64 queries µs | Mode |
|---:|---|---|---:|---|---:|---|
| 1,000 | uniform | Tedd.RTree (C#) | 0.037 | candidate | 15.43 | candidate |
| 1,000 | uniform | RBush (C#) | 0.304 | rbush | 115.89 | rbush |
| 1,000 | uniform | NTS STRtree (C#) | 0.385 | nts-list | 133.02 | nts-visitor |
| 1,000 | uniform | RTree (C#) | 0.768 | rtree | 114.61 | rtree |
| 1,000 | uniform | Enyim RTree (C#) | 0.295 | enyim | 818.88 | enyim |
| 1,000 | uniform | static_aabb2d_index (Rust) | 0.017 | native-static | 11.66 | native-static |
| 1,000 | uniform | geo-index Hilbert (Rust) | 0.042 | native-geo-hilbert | 27.76 | native-geo-hilbert |
| 1,000 | uniform | geo-index STR (Rust) | 0.035 | native-geo-str | 28.09 | native-geo-str |
| 1,000 | clustered | Tedd.RTree (C#) | 0.037 | candidate | 10.06 | candidate |
| 1,000 | clustered | RBush (C#) | 0.306 | rbush | 127.64 | rbush |
| 1,000 | clustered | NTS STRtree (C#) | 0.378 | nts-list | 116.31 | nts-visitor |
| 1,000 | clustered | RTree (C#) | 0.724 | rtree | 116.99 | rtree |
| 1,000 | clustered | Enyim RTree (C#) | 0.270 | enyim | 765.92 | enyim |
| 1,000 | clustered | static_aabb2d_index (Rust) | 0.020 | native-static | 10.48 | native-static |
| 1,000 | clustered | geo-index Hilbert (Rust) | 0.042 | native-geo-hilbert | 26.20 | native-geo-hilbert |
| 1,000 | clustered | geo-index STR (Rust) | 0.035 | native-geo-str | 25.94 | native-geo-str |
| 10,000 | uniform | Tedd.RTree (C#) | 0.405 | candidate | 77.78 | candidate |
| 10,000 | uniform | RBush (C#) | 6.070 | rbush | 922.66 | rbush |
| 10,000 | uniform | NTS STRtree (C#) | 5.820 | nts-visitor | 1069.00 | nts-visitor |
| 10,000 | uniform | RTree (C#) | 12.988 | rtree | 1355.89 | rtree |
| 10,000 | uniform | Enyim RTree (C#) | 5.474 | enyim | 8545.94 | enyim |
| 10,000 | uniform | static_aabb2d_index (Rust) | 0.592 | interop-static | 76.24 | native-static |
| 10,000 | uniform | geo-index Hilbert (Rust) | 0.613 | native-geo-hilbert | 128.54 | native-geo-hilbert |
| 10,000 | uniform | geo-index STR (Rust) | 0.593 | native-geo-str | 136.00 | native-geo-str |
| 10,000 | clustered | Tedd.RTree (C#) | 0.444 | candidate | 52.78 | candidate |
| 10,000 | clustered | RBush (C#) | 5.553 | rbush | 889.01 | rbush |
| 10,000 | clustered | NTS STRtree (C#) | 5.810 | nts-list | 898.24 | nts-visitor |
| 10,000 | clustered | RTree (C#) | 12.960 | rtree | 1267.37 | rtree |
| 10,000 | clustered | Enyim RTree (C#) | 4.824 | enyim | 8709.61 | enyim |
| 10,000 | clustered | static_aabb2d_index (Rust) | 0.558 | interop-static | 66.80 | native-static |
| 10,000 | clustered | geo-index Hilbert (Rust) | 0.611 | native-geo-hilbert | 107.68 | native-geo-hilbert |
| 10,000 | clustered | geo-index STR (Rust) | 0.576 | native-geo-str | 107.19 | native-geo-str |
| 100,000 | uniform | Tedd.RTree (C#) | 5.954 | candidate | 863.82 | candidate |
| 100,000 | uniform | RBush (C#) | 108.659 | rbush | 16101.46 | rbush |
| 100,000 | uniform | NTS STRtree (C#) | 82.412 | nts-list | 16014.71 | nts-visitor |
| 100,000 | uniform | RTree (C#) | 148.289 | rtree | 26358.79 | rtree |
| 100,000 | uniform | Enyim RTree (C#) | 84.991 | enyim | 103430.05 | enyim |
| 100,000 | uniform | static_aabb2d_index (Rust) | 7.683 | native-static | 1216.34 | native-static |
| 100,000 | uniform | geo-index Hilbert (Rust) | 6.817 | native-geo-hilbert | 1309.37 | native-geo-hilbert |
| 100,000 | uniform | geo-index STR (Rust) | 6.926 | interop-geo-str | 1303.28 | native-geo-str |
| 100,000 | clustered | Tedd.RTree (C#) | 6.880 | candidate | 808.61 | candidate |
| 100,000 | clustered | RBush (C#) | 91.444 | rbush | 20289.28 | rbush |
| 100,000 | clustered | NTS STRtree (C#) | 79.542 | nts-visitor | 17234.98 | nts-visitor |
| 100,000 | clustered | RTree (C#) | 146.994 | rtree | 26460.24 | rtree |
| 100,000 | clustered | Enyim RTree (C#) | 72.049 | enyim | 114815.49 | enyim |
| 100,000 | clustered | static_aabb2d_index (Rust) | 6.642 | native-static | 1271.43 | native-static |
| 100,000 | clustered | geo-index Hilbert (Rust) | 6.849 | native-geo-hilbert | 1335.92 | native-geo-hilbert |
| 100,000 | clustered | geo-index STR (Rust) | 6.390 | interop-geo-str | 1291.14 | native-geo-str |

## Method and limits

Ryzen 9 5950X, Windows 11, SDK 10.0.402/CoreCLR 10.0.13, Release x64, tiering disabled, affinity mask 4, capacity 16. Five shuffled fresh processes for every mode/fixture, seed 49217. Each operation calibrates to at least 100ms and measures one block. Construction precedes four query-width groups; the sum within each process forms its 64-query observation. The LCG seed 73211 and exact file bytes match the Rust fixture; this is not the older System.Random BenchmarkDotNet fixture. Geometry and item/query adapters are prepared before timing. Construction includes each API’s required working copies. Every returned ID is consumed, including visitor callbacks, rather than merely counting matching nodes.

All 180 processes check exact sorted result IDs against independent brute-force scans and check the timed checksum for every window before timing. All 24 empty/negative/contact/duplicate/reversed-input boundary cases pass. The sum visitor is reused and does not materialize a result list; allocating collection APIs retain their native allocation. This comparison includes those public API differences. No competitor implementation is rewritten.

Medians and min/max describe five process blocks. Fresh PIDs do not establish statistical independence; desktop activity, thermal/frequency variation and GC remain uncontrolled. Native and managed rows are separate sessions, not a paired statistical experiment. No significance, universal fastest ranking or tail latency is claimed. Current-thread allocation is not retained memory or working set. NTS and Rust selection uses complete mode medians per operation, never favorable individual samples.

The [contemporaneous Tedd reference](results/csharp-charts/tedd-reference.json) reports its complete fresh/previous ratios without normalization; earlier data remain unchanged. [Protocol](../Research/2026-10-18-csharp-charts/PROTOCOL.md), [full timing/allocation/ranges](results/csharp-charts/summary.csv), [raw observations](results/csharp-charts/samples.json), [process identities](results/csharp-charts/processes.json), [boundary results](results/csharp-charts/boundaries.json), [worker](csharp-charts/Worker.cs).

Reproduce in a dedicated task workspace: run `benchmarks/csharp-charts/locked.ps1 build`, then `measure`, `summarize.py` and `export.py`. All builds/measurements hold the shared performance mutex. Inspect package sources and execution paths before running; cleanup removes only owned disposable artifacts after shutdown.
