# Mutable R-tree and independent Rust indexes

Measured 18 October 2026. Tedd.RTree source `cf34a58` against release-1.0.12 source `79a5dd2`, static_aabb2d_index and geo-index (Hilbert/STR). This fixture uses the original mutable 2D double API. The [generic comparison](GENERIC-PACKED.md) measures the other 2D/3D APIs separately.

Each library runs independently. Rust scores use the lower whole-workload median of direct Rust and optimized interop. No favorable individual observations are selected. Native CPU optimization, thin LTO, one codegen unit and static unsafe_optimizations give competitors their optimized release configuration.

Interop uses blittable geometry, reused native output/traversal scratch where supported, zero-copy result views and no reverse managed callbacks. SuppressGCTransition applies to trivial result access and allocation-free static leaf queries bounded to 16 entries. Larger queries/builds keep ordinary transitions; direct execution removes interop entirely. Native construction includes destruction; managed reclamation occurs during repeated builds.

## Measurements

| Entries | Distribution | Library | Build ms | Mode | 64 queries µs | Mode |
|---:|---|---|---:|---|---:|---|
| 1,000 | uniform | Tedd.RTree (C#) | 0.036 | candidate | 15.23 | candidate |
| 1,000 | uniform | static_aabb2d_index (Rust) | 0.017 | native-static | 11.66 | native-static |
| 1,000 | uniform | geo-index Hilbert (Rust) | 0.042 | native-geo-hilbert | 27.76 | native-geo-hilbert |
| 1,000 | uniform | geo-index STR (Rust) | 0.035 | native-geo-str | 28.09 | native-geo-str |
| 1,000 | clustered | Tedd.RTree (C#) | 0.037 | candidate | 9.79 | candidate |
| 1,000 | clustered | static_aabb2d_index (Rust) | 0.020 | native-static | 10.48 | native-static |
| 1,000 | clustered | geo-index Hilbert (Rust) | 0.042 | native-geo-hilbert | 26.20 | native-geo-hilbert |
| 1,000 | clustered | geo-index STR (Rust) | 0.035 | native-geo-str | 25.94 | native-geo-str |
| 10,000 | uniform | Tedd.RTree (C#) | 0.391 | candidate | 77.36 | candidate |
| 10,000 | uniform | static_aabb2d_index (Rust) | 0.592 | interop-static | 76.24 | native-static |
| 10,000 | uniform | geo-index Hilbert (Rust) | 0.613 | native-geo-hilbert | 128.54 | native-geo-hilbert |
| 10,000 | uniform | geo-index STR (Rust) | 0.593 | native-geo-str | 136.00 | native-geo-str |
| 10,000 | clustered | Tedd.RTree (C#) | 0.437 | candidate | 51.95 | candidate |
| 10,000 | clustered | static_aabb2d_index (Rust) | 0.558 | interop-static | 66.80 | native-static |
| 10,000 | clustered | geo-index Hilbert (Rust) | 0.611 | native-geo-hilbert | 107.68 | native-geo-hilbert |
| 10,000 | clustered | geo-index STR (Rust) | 0.576 | native-geo-str | 107.19 | native-geo-str |
| 100,000 | uniform | Tedd.RTree (C#) | 6.765 | candidate | 867.29 | candidate |
| 100,000 | uniform | static_aabb2d_index (Rust) | 7.683 | native-static | 1216.34 | native-static |
| 100,000 | uniform | geo-index Hilbert (Rust) | 6.817 | native-geo-hilbert | 1309.37 | native-geo-hilbert |
| 100,000 | uniform | geo-index STR (Rust) | 6.926 | interop-geo-str | 1303.28 | native-geo-str |
| 100,000 | clustered | Tedd.RTree (C#) | 6.321 | candidate | 803.90 | candidate |
| 100,000 | clustered | static_aabb2d_index (Rust) | 6.642 | native-static | 1271.43 | native-static |
| 100,000 | clustered | geo-index Hilbert (Rust) | 6.849 | native-geo-hilbert | 1335.92 | native-geo-hilbert |
| 100,000 | clustered | geo-index STR (Rust) | 6.390 | interop-geo-str | 1291.14 | native-geo-str |

## Original API updates

These are the first 1,000 moves (or all entries for the 1k fixture), including first-use JIT work, unlike the generic warm64 mutation batches. Do not infer sustained throughput from these single cold batches.

| Entries | Distribution | 1.0.12 moves ms | Current moves ms | 1.0.12 post-query µs | Current post-query µs |
|---:|---|---:|---:|---:|---:|
| 1,000 | uniform | 12.659 | 12.522 | 16.38 | 16.72 |
| 1,000 | clustered | 12.847 | 12.775 | 10.77 | 10.61 |
| 10,000 | uniform | 14.344 | 13.857 | 96.99 | 97.20 |
| 10,000 | clustered | 14.221 | 13.899 | 63.35 | 62.92 |
| 100,000 | uniform | 20.205 | 18.348 | 1218.25 | 1322.19 |
| 100,000 | clustered | 17.183 | 16.408 | 1041.71 | 1023.53 |

## Method, provenance and limits

240 scheduled fresh processes completed: six deterministic fixtures, eight arms, five replications; shuffled seed81043. Source/caller/native hashes, all raw observations, launches and failure policy are retained in [the protocol](results/mutation-regressions/cross/protocol.json). Every implementation validates all 64 query result sets against brute force before timing. Node capacity16, one CPU affinity (mask4), Release x64, .NET10.0.13 with tiering disabled. Each operation calibrates to at least100ms, then measures one block. The query aggregate is the median of each process’s sum of four 16-window groups. IDs are materialized and consumed.

Geometry uses LCG seed73211; uniform coordinates or eight diagonal clusters, boxes of widths1–5, query widths0/20/200/1000. This older two-dimensional fixture differs from the dimension-specific generic fixture. Fixture parsing and prepared geometry are excluded from timing. Both before/after managed arms use an identical caller binary.

Pinned sources: [static_aabb2d_index a511a63](https://github.com/jbuckmccready/static_aabb2d_index/tree/a511a6327e14a0f0418cea01c401bf147e0e835c), [geo-index e6efbb0](https://github.com/georust/geo-index/tree/e6efbb01d3c298e8963c8b7d1aab40c1bd540715). Source/build paths and dependencies were inspected before execution; this is a limited review, not a security audit. See [native provenance](results/mutation-regressions/cross/native-provenance.json) and [review record](../Research/2026-10-18-mutation-regressions/NATIVE-REVIEW.md).

Desktop load, frequency/thermal variation and runtime scheduling are uncontrolled beyond the shared cooperating-host mutex. Fresh PIDs do not prove independence; medians/ranges are descriptive. These measurements establish neither a universal fastest library nor individual tail latency. Native allocations are unavailable, not zero; managed counters cover the current thread, not retained memory. The earlier C/C++/Go/JavaScript screening remains in [CROSS-LANGUAGE.md](CROSS-LANGUAGE.md).

Complete [medians/ranges/allocations](results/mutation-regressions/cross/summary.csv), [samples](results/mutation-regressions/cross/samples.json), [native boundaries](results/mutation-regressions/cross/native-boundaries.json), and [mutation investigation](../Research/2026-10-18-mutation-regressions/REPORT.md).
