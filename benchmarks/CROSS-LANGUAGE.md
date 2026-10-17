# Cross-language spatial-index comparison

Measured 2026-10-17 against Tedd.RTree commit `9d8fb597932bca550ab7d7092af6b35c5a15a09b`.

Eight competing libraries were screened and benchmarked across C, C++, Go, Rust, and JavaScript. These measurements identify winners for the tested workloads; they do not establish a universal fastest spatial index.

`static_aabb2d_index` had the lowest aggregate query median in 6 of six fixtures. Tedd’s bulk-loaded reused-list query time divided by its query time ranged from 1.29× to 2.13×. At 100,000 entries, Tedd bulk construction time divided by `geo-index` Hilbert construction time ranged from 3.71× to 4.06×. Both competitors are immutable packed indexes. Wide queries dominate the aggregate mix; selective-query rankings differ.

## Results across fixture sizes

Each cell uses the median of five fresh-process block averages. “Tedd / winner” is the ratio of Tedd bulk/reused time to the fastest measured time; a larger ratio means Tedd took longer. Aggregate query time is the sum of four separately timed 16-query groups within each process, followed by the median across processes.

| Entries | Distribution | Fastest construction | Tedd / winner | Fastest aggregate queries | Tedd / winner |
|---:|---|---|---:|---|---:|
| 1,000 | uniform | static_aabb2d_index | 4.77× | static_aabb2d_index | 2.13× |
| 1,000 | clustered | static_aabb2d_index | 3.59× | static_aabb2d_index | 1.82× |
| 10,000 | uniform | geo-index STR | 5.57× | static_aabb2d_index | 1.89× |
| 10,000 | clustered | static_aabb2d_index | 5.94× | static_aabb2d_index | 1.61× |
| 100,000 | uniform | geo-index Hilbert | 4.06× | static_aabb2d_index | 1.29× |
| 100,000 | clustered | geo-index Hilbert | 3.71× | static_aabb2d_index | 1.32× |

## 100,000 entries: uniform

Construction is milliseconds per new index/lifecycle operation. Query columns are microseconds per 16 queries; lower is faster.

| Library/API | Build ms | Point | Width 20 | Width 200 | Width 1,000 | Aggregate 64 µs |
|---|---:|---:|---:|---:|---:|---:|
| Tedd bulk reused | 29.079 | 4.14 | 10.46 | 208.38 | 1239.03 | 1462.23 |
| Tedd bulk allocating | 29.109 | 4.39 | 12.63 | 259.32 | 3064.32 | 3340.38 |
| Tedd incremental | 132.325 | 9.58 | 21.58 | 500.20 | 2457.91 | 2989.86 |
| Tidwall C | 13.550 | 2.47 | 5.88 | 254.51 | 1667.85 | 1931.60 |
| Tidwall Go | 26.112 | 3.24 | 10.19 | 418.71 | 2801.86 | 3235.34 |
| Superliminal C++ | 74.755 | 6.28 | 14.09 | 503.94 | 3007.47 | 3531.81 |
| Boost.Geometry packed | 20.657 | 7.31 | 16.39 | 476.03 | 3142.76 | 3644.47 |
| Boost.Geometry visitor | 20.542 | 1.68 | 5.87 | 194.71 | 1372.34 | 1574.08 |
| rstar bulk | 25.337 | 1.88 | 8.79 | 390.54 | 2858.18 | 3259.29 |
| geo-index Hilbert | 7.171 | 4.04 | 12.28 | 257.21 | 2110.74 | 2386.60 |
| geo-index STR | 7.647 | 4.00 | 12.25 | 252.11 | 1646.82 | 1916.15 |
| static_aabb2d_index | 8.282 | 2.06 | 4.71 | 141.70 | 988.72 | 1136.96 |
| Flatbush | 20.433 | 7.10 | 21.69 | 461.70 | 4349.30 | 4838.55 |

## 100,000 entries: clustered

Construction is milliseconds per new index/lifecycle operation. Query columns are microseconds per 16 queries; lower is faster.

| Library/API | Build ms | Point | Width 20 | Width 200 | Width 1,000 | Aggregate 64 µs |
|---|---:|---:|---:|---:|---:|---:|
| Tedd bulk reused | 25.862 | 0.68 | 0.60 | 261.35 | 1304.88 | 1567.19 |
| Tedd bulk allocating | 28.718 | 0.70 | 0.63 | 606.49 | 3099.53 | 3675.91 |
| Tedd incremental | 133.934 | 0.27 | 0.25 | 454.12 | 2266.22 | 2720.86 |
| Tidwall C | 12.986 | 0.29 | 0.31 | 318.56 | 1709.05 | 2029.88 |
| Tidwall Go | 27.686 | 0.75 | 0.93 | 555.09 | 2947.53 | 3504.32 |
| Superliminal C++ | 76.281 | 0.20 | 0.22 | 580.00 | 3125.13 | 3705.74 |
| Boost.Geometry packed | 17.552 | 2.27 | 2.27 | 687.20 | 3319.66 | 3999.70 |
| Boost.Geometry visitor | 17.262 | 0.26 | 0.29 | 272.60 | 1450.45 | 1727.57 |
| rstar bulk | 22.105 | 0.23 | 0.23 | 537.34 | 3050.98 | 3583.06 |
| geo-index Hilbert | 6.973 | 1.14 | 1.18 | 298.33 | 1694.40 | 1997.58 |
| geo-index STR | 7.426 | 1.15 | 1.13 | 299.48 | 1623.63 | 1925.91 |
| static_aabb2d_index | 7.197 | 0.32 | 0.38 | 187.62 | 997.63 | 1185.43 |
| Flatbush | 20.627 | 1.68 | 1.80 | 779.84 | 4933.14 | 5693.13 |

## Query result volumes

Total matches across each 16-query group, counting an entry again when it matches another query. Several clustered selective-query groups have no matches; their timings measure rejection/traversal.

| Entries | Distribution | Point hits | Width 20 hits | Width 200 hits | Width 1,000 hits |
|---:|---|---:|---:|---:|---:|
| 1,000 | uniform | 0 | 13 | 552 | 3,774 |
| 1,000 | clustered | 0 | 0 | 1,244 | 4,289 |
| 10,000 | uniform | 2 | 98 | 6,070 | 31,853 |
| 10,000 | clustered | 0 | 0 | 4,707 | 34,682 |
| 100,000 | uniform | 33 | 888 | 55,678 | 453,353 |
| 100,000 | clustered | 0 | 0 | 92,206 | 499,780 |

## Libraries and execution paths

| Library | Construction | Mutation after construction | Query output |
|---|---|---|---|
| Tedd.RTree (.NET) | STR bulk; separate incremental variant | Supported | Reused `List<int>`; separate allocating variant |
| [Tidwall C](https://github.com/tidwall/rtree.c) | Incremental | Supported | Callback into reused ID vector |
| [Tidwall Go](https://github.com/tidwall/rtree) | Incremental | Supported | Generic integer payload; callback into reused ID slice |
| [Superliminal C++](https://github.com/nushoin/RTree) | Incremental | Supported | Callback into reused ID vector |
| [Boost.Geometry](https://www.boost.org/doc/libs/latest/libs/geometry/doc/html/geometry/spatial_indexes/rtree_quickstart.html) | Packed range constructor, `rstar<16>` | Supported | `qbegin`; supplementary `query` output iterator |
| [GeoRust rstar](https://github.com/georust/rstar) | Bulk | Supported | Intersection iterator into reused ID vector |
| [GeoRust geo-index](https://github.com/georust/geo-index) | Hilbert or STR packing | Immutable | Allocating search |
| [static_aabb2d_index](https://github.com/jbuckmccready/static_aabb2d_index) | Hilbert packing | Immutable | Visitor with reused ID vector and traversal stack |
| [Flatbush](https://github.com/mourner/flatbush) | Hilbert packing | Immutable | Allocating search |

Node capacities are 16 except Tidwall C/Go (upstream default 64) and `rstar` (upstream default 6). No node-capacity tuning sweep was performed. Source snapshots are pinned in [sources.lock.json](cross-language/sources.lock.json), including development snapshots whose manifest versions need not represent published releases.

## Source screening before execution

- Reviewed indexing entry points, imports, allocation/callback paths, manifests, and dependency build scripts. The worker execution paths perform in-memory indexing and fixture reads, with no database or network operations.
- C uses ordinary allocation and reference-counted nodes; Go uses documented unsafe node-layout conversions. Superliminal has optional serialization methods, which the worker never calls. Boost uses header-only index construction/search.
- `rstar` forbids unsafe code in its own crate. `geo-index` uses unchecked slice indexing; reviewed its builder and search bounds. `static_aabb2d_index` was compiled with its default safe configuration and forbids unsafe code in that configuration.
- Flatbush and its sole runtime dependency FlatQueue contain array/index/queue operations. Dependencies were copied from reviewed sources; npm hooks were not run.
- Rust dependency build scripts perform compiler-capability probes and generate configuration files under the task workspace. Compiler subprocesses and generated-file paths were inspected before compilation. No upstream benchmark, demonstration, installer, or deployment scripts ran.
- The portable Go archive was verified against the SHA-256 supplied by the official Go download service. This was a limited source/reputation screening, not a comprehensive security audit.

## Measurement conditions and limits

AMD Ryzen 9 5950X; Windows 10.0.26200 x64; .NET runtime 10.0.13 / SDK 10.0.402; Clang 22.1.3; Rust 1.93.1; Go 1.27.2; Node 24.11.1. C/C++ use `-O3 -DNDEBUG -march=native`; Rust uses release optimization, thin LTO, one codegen unit, and `target-cpu=native`. .NET tiered compilation is disabled; this differs from the earlier BenchmarkDotNet comparison, which retained default tiering/PGO.

Five fresh processes per library/fixture, serial execution, Windows affinity mask `4` (logical CPU 2), 100 ms minimum discarded calibration followed by a block with the same repetition count. Process/block averages describe throughput, not per-request tail latency. Background activity and power policy were uncontrolled. Observed ranges are retained in the raw summaries; no formal significance test or cross-machine claim is made.

All implementations receive identical integer-valued 2D double-precision rectangles and inclusive-intersection queries. Fixture generation uses a fixed LCG; the seed, code, fixture hashes, and hit counts are retained. Result IDs are fully materialized and consumed. Every process verifies exact sorted result IDs against brute force before timing. The separate four-entry probes exercise duplicate bounds, negative coordinates, zero-area rectangles, edge contact, complete coverage, and no matches.

Construction includes required input copies and normal object lifetime/reclamation costs. Native/Rust destruction is synchronous; managed runtimes reclaim indexes through GC. Geometry preparation and fixture parsing are outside timing. These are construction/lifecycle costs rather than allocator-independent build times. Immutable indexes have a different contract from mutable trees. Memory footprint, concurrent access, updates/removals, 3D, noninteger geometry, real-world datasets, and more than 100,000 entries are not measured.

Payload and result-buffer representations follow each native API; their element widths and runtime overheads differ. This compares usable library configurations, not language execution cost in isolation. Compiler flags, node capacities, and allocation policies are disclosed rather than treated as identical.

Boost’s output-iterator API and `static_aabb2d_index` form a supplementary cohort run after the primary cohort with the same fixtures and timing policy. Their process ranges and cohort identity remain separate. Treat small cross-cohort differences cautiously.

## Evidence and reproduction

[Harness and instructions](cross-language/REPRODUCE.md); [source/compiler identities](cross-language/sources.lock.json); [primary samples](results/cross-language/samples.json); [primary operation medians/ranges](results/cross-language/summary.csv); [supplementary samples](results/cross-language-supplementary/samples.json); [supplementary operation medians/ranges](results/cross-language-supplementary/summary.csv); [combined aggregate comparison](results/cross-language/aggregate.csv); [fixture hashes and hit counts](results/cross-language/fixtures.json).

The existing Tedd.RTree differential and boundary test executable passed in Release. All 390 benchmark processes and 13 boundary-probe processes passed their exact result-set checks (25,012 query/result-set comparisons). No production implementation changes were made.
