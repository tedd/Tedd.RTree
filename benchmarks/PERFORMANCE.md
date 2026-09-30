# R-tree performance record

The [five-package comparison](PACKAGE-COMPARISON.md) is the current website dataset. It uses identical integer-valued geometry across double, float, and integer APIs and validates result IDs before timing. The historical records below use a different fixture. Their original query-width selector produced widths 0 through 63, rather than the intended repeating 0/20/200/1,000-unit windows; interpret those archived query timings accordingly.

For later tests of caller-owned scratch, query caching, SIMD scans, and bitmap compaction, see [the hypothesis record](HYPOTHESES.md).
For parallel searches and moving-entry concurrency, see [the concurrency record](CONCURRENCY.md).

## Reproduce

```powershell
dotnet build Tedd.RTree.sln -c Release
dotnet run --project tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj -c Release --no-build
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*SpatialBenchmarks*'
```

The focused final comparison used the same command with these filters: `*Build_Tedd_Bulk*`, `*Build_RBush_Bulk*`, `*Build_Nts*`, `*Query_Tedd_Bulk*`, `*Query_RBush_Bulk*`, `*Query_Nts*`. Raw BenchmarkDotNet exports are in [results](results/); [final-comparison.csv](results/final-comparison.csv) contains the bulk build and query comparisons. Earlier experiments retain their own CSV files and source snapshots. The starting repository commit was `e10fd47`. SHA-256 of `RTree.cs` when this comparison was recorded was `8257D94C6B795CCC14854F79319298132DAC17E5EF7977E6D31C297ED07E56CA`; the benchmark fixture was `D79F6D7C5B0A3D21F16840CA722BE7E363A33BBC182695DF03D639128CB1C78B`.

Measured on Windows 10.0.26200, AMD Ryzen 9 5950X, x64, .NET 10.0.12 RyuJIT, Concurrent Workstation GC. SDK 10.0.401 and BenchmarkDotNet 0.15.8. Default tiering and dynamic PGO were left enabled. Each ShortRun job used one launch, three warmups, and three measured iterations. No affinity or power-policy control was imposed. Results are local estimates, not cross-machine guarantees.

Fixtures use seed 73211, node capacity 16, 1,000 or 10,000 rectangles, and uniform or eight-cluster placement. Each query benchmark performs the same 64 windows of widths 0, 20, 200, and 1,000, and consumes the match count. Geometry and package adapter objects are prepared in `GlobalSetup`; construction includes the tree's insertion, bulk load, or STRtree `Build`. The allocating Tedd.RTree query path creates a result list, as the package query APIs do. The reused-list path is reported separately. Every adapter's result count is checked against a linear scan before timing.

## Final bulk comparison

Mean ± sample standard deviation per complete build, in microseconds:

| Entries | Distribution | Tedd.RTree STR | RBush bulk | NTS STRtree |
|---:|---|---:|---:|---:|
| 1,000 | Clustered | 102 ± 9 | 216 ± 2 | 221 ± 0.3 |
| 1,000 | Uniform | 85 ± 3 | 288 ± 15 | 270 ± 3 |
| 10,000 | Clustered | 2,564 ± 32 | 4,469 ± 187 | 3,657 ± 23 |
| 10,000 | Uniform | 2,299 ± 176 | 4,725 ± 69 | 3,832 ± 76 |

Mean ± sample standard deviation per batch of 64 queries, in microseconds. Tedd.RTree uses the allocating path:

| Entries | Distribution | Tedd.RTree STR | RBush bulk | NTS STRtree |
|---:|---|---:|---:|---:|
| 1,000 | Clustered | 1.74 ± 0.04 | 4.10 ± 0.03 | 2.62 ± 0.02 |
| 1,000 | Uniform | 5.67 ± 0.07 | 11.63 ± 0.60 | 16.33 ± 0.20 |
| 10,000 | Clustered | 4.81 ± 0.09 | 10.93 ± 0.20 | 14.91 ± 0.32 |
| 10,000 | Uniform | 14.41 ± 0.02 | 33.89 ± 0.23 | 64.38 ± 0.24 |

At 10,000 uniform entries, construction allocated 1,339,719 B for Tedd.RTree, 2,217,488 B for RBush bulk, and 1,433,358 B for NTS. The corresponding query batches allocated 16,112 B, 34,352 B, and 16,112 B. The reused-list Tedd.RTree path allocated 0 B in the measured query batches. [The raw export](results/final-comparison.csv) contains every fixture, allocation count, and unrounded estimate.

These workloads do not measure input object creation, deletion, concurrent access, larger data sets, or latency tails. RBush also offers a different bulk algorithm and a mutable index; STRtree stops accepting inserts after its build. The reported build and query numbers should be weighed together for the intended update-to-query ratio.

The alternatives' construction methods explain the initial gap against individual insertion. [RBush](https://www.nuget.org/packages/RBush/4.0.0) documents overlap minimizing top-down bulk loading with Floyd–Rivest selection and small-tree-large-tree merging into an existing index. [NetTopologySuite STRtree](https://nettopologysuite.github.io/NetTopologySuite/api/NetTopologySuite.Index.Strtree.STRtree-1.html) uses Sort-Tile-Recursive packing and builds its query tree after the insert batch. Tedd.RTree now uses STR packing for its own bulk path. The timings compare implementations and APIs on specified data; they do not establish an intrinsic ranking of these algorithms.

## Optimization experiments

| Candidate | Evidence and decision |
|---|---|
| Incremental parent bounds | **Retained.** Replaced an O(node capacity) bound rescan on each insertion path with a union. On the initial 10,000-entry workloads, construction fell from 11.33 to 7.07 ms clustered and from 8.25 to 7.16 ms uniform. The first baseline used a preview SDK, although both workers ran .NET 10; treat this comparison as directional. [Baseline](results/initial-baseline.csv), [candidate](results/incremental-bounds.csv), [source snapshot](results/initial-RTree.txt). |
| Stack scratch for split assignment | **Rejected.** Replacing the bounded `bool[]` with `stackalloc` reduced allocation but increased 10,000-entry construction from 7.06 to 10.28 ms clustered and from 7.09 to 10.65 ms uniform. [Before](results/pre-stack-scratch.csv), [after](results/stack-scratch.csv). |
| Internal unchecked rectangle union | **Retained.** Validated rectangles can be unioned without rerunning public constructor validation. Separate 10,000-entry runs moved from 7.36 to 6.07 ms clustered and 7.00 to 6.35 ms uniform. [Before](results/pre-unchecked-union.csv), [after](results/unchecked-union.csv). This was tested before the packed builder was introduced. |
| STR bulk packing | **Retained.** A batch sort and bottom-up node construction avoids individual insertion paths. The first packed version built 10,000 entries in about 4.0 ms; query speed depended on distribution. [First full comparison](results/final-bulk.csv). |
| Sort indices instead of wide entries | **Retained.** A [sampled trace](results/bulk-profile-initial-topN.txt) attributed 82.6% of exclusive bulk-build samples to `IntroSort` with 48-byte entries. Sorting integer positions reduced 10,000-entry build time from 4.02 to 2.99 ms clustered and 4.03 to 2.93 ms uniform, at about 42 KB more allocation. [Before](results/final-bulk.csv), [after](results/index-sort.csv), [source before](results/pre-index-sort-RTree.txt), [source after](results/index-sort-RTree.txt). |
| Precompute axis centers | **Retained.** Center coordinates were previously recomputed for every comparator call. At 10,000 entries, build time fell from 2.99 to 2.18 ms clustered and from 2.93 to 2.29 ms uniform; allocation rose by about 167 KB. [Before](results/index-sort.csv), [after](results/precomputed-centers.csv). The independent final comparison measured 2.56 and 2.30 ms. |

After the last change, sampled sorting still accounted for 76.0% of exclusive bulk-build samples; node packing accounted for 8.5%. [Top methods](results/bulk-profile-topN.txt). This sample attribution includes runtime sort internals and does not identify a specific instruction bottleneck. No unsafe access or ISA-specific code was introduced.

## Candidate coverage

| Catalogue IDs | Inspected path and disposition |
|---|---|
| M1, M2 | `Split` uses a temporary entry snapshot and assignment buffer; bounded stack storage was tested and rejected. Long-lived node arrays are charged to build allocation. A pool would require clearing managed references on return and is not supported by a measured allocation bottleneck after bulk packing. |
| M3, M4 | `Node.Entries` uses one-dimensional arrays and query uses `ref` entries. No sampled evidence isolated range-check overhead; unsafe indexing lacks a justified benefit and was not used. |
| M5, M6, M7 | `PackLevel` changed from sorting wide entries to indices and cached centers. Both changes were tested and retained, including their allocation costs. |
| C1, C2, C3, C4 | The sampled build bottleneck is library sorting. Search is irregular branch-driven traversal; no independent lane-wise kernel, bit loop, or identified branch-miss or instruction-latency problem justified an intrinsic experiment. |
| S1, S2, S3, S5 | No bitmap, hash lookup, frozen map, or compressible run is used in this spatial index. |
| S4 | Batch preparation and packed tree construction were implemented and compared with incremental insertion. |
| R1, R2, R3 | No reflection, feature flag, boxing, or polymorphic item accessor appears in the index hot path. Sort comparison work was reduced by cached centers; further dispatch changes had no isolated evidence. |
| T1, T2, T3, T4 | This tree has no internal concurrency protocol or synchronization. Concurrent mutation is outside its contract, so false sharing, locks, and scheduling candidates do not apply. |

The catalogue records evidence for this implementation and fixture set. It does not establish that every possible sorter, split policy, or workload has been optimized.
