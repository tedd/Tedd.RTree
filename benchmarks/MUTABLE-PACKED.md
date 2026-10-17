# Mutable packed-tree comparison

Measured 2026-10-17. Candidate source: `a5d902c`; unchanged control library from `e79bd96` (same production code as the preceding cross-language comparison). Scope: original mutable `RTree<T>` with 2D double coordinates. Generic 2D/3D trees remain regression-tested.

Hilbert ordering, radix sorting, and bottom-up packing reduce construction work. Separate bounds/value/child arrays enable bulk copying fully contained leaves. Existing insertion, splitting, removal, condensation, and update paths remain active; mutation triggers no conversion or rebuild.

At 100,000 entries, construction improved 4.18–4.40× and aggregate queries improved 1.72–2.01× against the unchanged control. Tedd’s aggregate query median was lower than both Rust indexes in five of six fixtures; static_aabb2d_index remained faster for 1,000 uniform entries and usually for the most selective queries. The 10,000-uniform aggregate margin is only about 1%, which should not be treated as a robust ranking. At 100,000 entries, Tedd took 0.865/0.810 ms for aggregate queries versus static’s 1.222/1.276 ms (uniform/clustered).

## Fresh-process confirmation

Each cell is the median of five fresh-process block averages. Queries materialize all IDs and consume them; the aggregate is the median of each process’s sum of four 16-query groups. Lower is faster. Ranges and allocations are in [summary.csv](results/mutable-packed/confirmation/summary.csv); all samples, launch records, and prospective shuffled schedules are retained alongside it.

| Entries | Distribution | Old build ms | New build ms | Build speedup | Old 64 queries µs | New 64 queries µs | Query speedup |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1,000 | uniform | 0.087 | 0.038 | 2.29× | 23.55 | 15.13 | 1.56× |
| 1,000 | clustered | 0.084 | 0.036 | 2.32× | 17.00 | 9.72 | 1.75× |
| 10,000 | uniform | 3.633 | 0.422 | 8.60× | 133.37 | 77.38 | 1.72× |
| 10,000 | clustered | 3.664 | 0.445 | 8.22× | 95.52 | 52.16 | 1.83× |
| 100,000 | uniform | 29.918 | 6.802 | 4.40× | 1490.87 | 865.46 | 1.72× |
| 100,000 | clustered | 26.256 | 6.289 | 4.18× | 1627.16 | 809.63 | 2.01× |

## Competitors

Pinned revisions: [`static_aabb2d_index`](https://github.com/jbuckmccready/static_aabb2d_index/tree/a511a6327e14a0f0418cea01c401bf147e0e835c), [`geo-index`](https://github.com/georust/geo-index/tree/e6efbb01d3c298e8963c8b7d1aab40c1bd540715). Rust release uses native CPU instructions, thin LTO, one codegen unit, and static index `unsafe_optimizations`. Source indexing paths and dependency build scripts were inspected before execution; this was a limited review, not a security audit.

Each competitor has direct Rust and C ABI measurements. Direct construction measures the index alone, excluding bridge output/scratch setup. Interop uses blittable geometry, zero-copy result views, no reverse managed callbacks, and reused traversal scratch/output where supported. `[SuppressGCTransition]` is used on trivial result access and allocation-free static leaf queries bounded to 16 entries. Builds and larger searches retain ordinary transitions, as required by the [runtime contract](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.suppressgctransitionattribute). Direct Rust eliminates interop entirely. The tables give each competitor the lower **whole-workload median** of direct and interop execution; individual favorable samples are never selected.

The Rust indexes are immutable. Tedd retains mutability. Native destruction is included in construction; managed construction leaves reclamation to GC during repeated builds. Allocation figures cover managed current-thread allocations only; unavailable native allocation is recorded as unavailable.


### 1,000 entries, uniform

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 0.038 (candidate) | 0.89 | 0.94 | 3.73 | 9.57 | 15.13 (candidate) |
| static | 0.017 (native-static) | 0.65 | 0.68 | 2.32 | 8.07 | 11.72 (native-static) |
| geo-hilbert | 0.042 (native-geo-hilbert) | 1.54 | 1.78 | 6.72 | 17.91 | 27.88 (native-geo-hilbert) |
| geo-str | 0.034 (native-geo-str) | 1.33 | 1.73 | 6.80 | 18.44 | 28.30 (native-geo-str) |

### 1,000 entries, clustered

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 0.036 (candidate) | 0.20 | 0.33 | 2.90 | 6.29 | 9.72 (candidate) |
| static | 0.020 (native-static) | 0.19 | 0.27 | 2.57 | 7.40 | 10.43 (native-static) |
| geo-hilbert | 0.042 (native-geo-hilbert) | 0.88 | 0.99 | 7.15 | 17.54 | 26.45 (native-geo-hilbert) |
| geo-str | 0.034 (native-geo-str) | 0.88 | 0.99 | 7.15 | 17.65 | 26.48 (native-geo-str) |

### 10,000 entries, uniform

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 0.422 (candidate) | 1.54 | 2.10 | 19.93 | 53.74 | 77.38 (candidate) |
| static | 0.562 (interop-static) | 1.34 | 1.63 | 15.72 | 59.63 | 78.40 (native-static) |
| geo-hilbert | 0.627 (native-geo-hilbert) | 2.22 | 3.54 | 29.89 | 92.66 | 128.47 (native-geo-hilbert) |
| geo-str | 0.588 (native-geo-str) | 2.20 | 3.84 | 30.75 | 100.59 | 137.32 (native-geo-str) |

### 10,000 entries, clustered

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 0.445 (candidate) | 0.41 | 0.31 | 7.94 | 43.51 | 52.16 (candidate) |
| static | 0.526 (interop-static) | 0.33 | 0.26 | 8.64 | 58.37 | 68.03 (native-static) |
| geo-hilbert | 0.608 (native-geo-hilbert) | 1.06 | 0.93 | 15.08 | 91.20 | 108.26 (native-geo-hilbert) |
| geo-str | 0.564 (native-geo-str) | 1.05 | 0.89 | 15.05 | 91.23 | 108.38 (native-geo-str) |

### 100,000 entries, uniform

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 6.802 (candidate) | 2.20 | 6.96 | 138.47 | 717.37 | 865.46 (candidate) |
| static | 7.765 (native-static) | 1.82 | 4.40 | 147.87 | 1066.72 | 1222.33 (native-static) |
| geo-hilbert | 7.002 (native-geo-hilbert) | 2.99 | 9.50 | 189.41 | 1722.86 | 1923.11 (native-geo-hilbert) |
| geo-str | 7.093 (interop-geo-str) | 2.98 | 9.63 | 183.12 | 1110.12 | 1305.84 (native-geo-str) |

### 100,000 entries, clustered

| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |
|---|---:|---:|---:|---:|---:|---:|
| Tedd mutable | 6.289 (candidate) | 0.33 | 0.38 | 142.28 | 666.97 | 809.63 (candidate) |
| static | 6.733 (native-static) | 0.27 | 0.31 | 203.70 | 1072.03 | 1276.31 (native-static) |
| geo-hilbert | 6.798 (native-geo-hilbert) | 0.96 | 0.98 | 205.71 | 1154.31 | 1360.77 (native-geo-hilbert) |
| geo-str | 6.664 (native-geo-str) | 0.97 | 0.97 | 205.48 | 1455.64 | 1662.74 (native-geo-str) |

## Mutation and allocation guardrails

After bulk loading, each managed process moves the first min(N, 1,000) entries using public `Update`, validates every result against brute force, then measures the same query groups. Move batches are timed once per process and include first-use JIT work; they have less repetition and greater startup sensitivity than the primary metrics. These measured batches regressed by up to 14.2% in the smaller fixtures and 9.3% at 100k uniform; 100k clustered was slightly faster. Adoption accepts this disclosed guardrail tradeoff for the primary build/query improvements. These data do not establish steady-state update throughput. Post-move aggregate queries improved in all six fixtures; build allocations fell by approximately 53% at 100k.

| Entries | Distribution | Old moves ms | New moves ms | Old post-move queries µs | New post-move queries µs | Old build bytes | New build bytes |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1,000 | uniform | 11.118 | 12.697 | 23.82 | 16.75 | 136,928 | 60,368 |
| 1,000 | clustered | 11.440 | 12.894 | 16.50 | 10.00 | 136,928 | 60,368 |
| 10,000 | uniform | 12.592 | 14.379 | 155.90 | 101.84 | 1,339,842 | 626,864 |
| 10,000 | clustered | 13.050 | 14.318 | 117.67 | 68.06 | 1,339,738 | 626,864 |
| 100,000 | uniform | 18.676 | 20.409 | 2028.63 | 1229.79 | 13,344,602 | 6,242,897 |
| 100,000 | clustered | 17.532 | 17.329 | 1919.02 | 1001.49 | 13,344,658 | 6,242,906 |

## Method and limits

Windows 11 build 26200, Ryzen 9 5950X, .NET SDK 10.0.402/runtime 10.0.13, Rust 1.93.1 MSVC. CPU affinity mask 4, single worker at a time, shared host mutex, tiering disabled. Calibration doubles repetitions to at least 100 ms; one subsequent block is measured. Six fixed-seed fixtures, query widths 0/20/200/1000, five blocks × eight workers × six fixtures = 240 validated process launches. No failed or excluded confirmation samples. Other desktop activity remains uncontrolled; process blocks are descriptive repetitions, not proof of statistical independence.

Correctness covers exact result multisets before/after mutation, inclusive edges, duplicates, reference values, extreme finite doubles/subnormals, capacities 4/5/16/128, root collapse, workspace reuse across original/generic implementations, indexed-only input lists, and append semantics. Supplemental interop checks passed for 0/1/16/17 entries in all three modes, including duplicate bounds, negative coordinates, and edge contacts; their timings are excluded. The comparisons use integer-valued geometry represented exactly as double. Rankings do not establish a universal fastest index, nor characterize continuous random coordinates, sustained update-heavy workloads, other capacities, platforms, or large user payloads.

DotNetLab was applied after the algorithm commit. CPU captures and full optimized JIT listings guided representation, copy, sorting, and predicate changes. Diagnostic targets were separate from timed workers. The ordinary external target does not qualify for DotNetLab’s native promotion lane; adoption rests on the reproducible normal-build external comparison. Candidate ledger, rejected experiments, capture IDs, source findings, and artifacts: [research record](../Research/2026-10-17-mutable-packed/REPORT.md).

Reproduction: stage the pinned Rust sources under a designated task workspace; use `mutable-packed/native.ps1` to fetch, inspect dependencies, and build. Preserve the control library with its original source, build both managed workers using `mutable-packed/locked.ps1`, run action `confirmation`, then execute `mutable-packed/summarize.py`. The checked-in protocol identifies binary hashes, exact launch order, calibration, and environment. Scratch paths are disposable; source, scripts, and evidence remain in this repository.
