# Storage, cache, and scan hypothesis record

## Reproduce

```powershell
dotnet build Tedd.RTree.sln -c Release
dotnet run --project tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj -c Release --no-build
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --validate-hypotheses
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*WorkspaceBuildBenchmarks*'
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*RecentQueryCacheBenchmarks*' '*OutputStorageBenchmarks*' '*IndexBuildBenchmarks*' '*ScanHypothesisBenchmarks*' '*ByteSpanBenchmarks*' '*CrossoverBenchmarks*'
```

The executable fixtures are in [HypothesisBenchmarks.cs](Tedd.RTree.Benchmarks/HypothesisBenchmarks.cs). Raw BenchmarkDotNet exports are in [results/hypotheses](results/hypotheses/). They record all cases, allocation counts, variability, and job settings. The benchmark suite uses uniform rectangles within a 1,000 × 1,000 coordinate region, seed 73211, node capacity 16, and 64 query windows per query operation. Indexes and query inputs are prepared before query timing; build methods time index construction from prepared rectangles. Results are appended to a reused list unless the method explicitly tests list allocation. All candidate results are checked against either a linear intersection reference or the packed tree before timing. Separate validation covers zero, short, partial-vector, and edge-contact cases, including a run with hardware intrinsics disabled.

Measured on Windows 11 10.0.26200, AMD Ryzen 9 5950X, .NET 10.0.12 x64 RyuJIT x86-64-v3, SDK 10.0.401, and BenchmarkDotNet 0.15.8. ShortRun used one launch, three warmups, and three measured iterations. No affinity was pinned. Measurements are local estimates. A run interrupted after competing applications started is excluded; [byref-clean.csv](results/hypotheses/byref-clean.csv) is its replacement. The starting repository commit was `b5158be`; the experiments add the source named above. The first scan export predates the workspace overload but uses the same R-tree algorithm. Source SHA-256 for that scan fixture was `597932704521A5384987128609C2836D8D267733530C46C992B418FD2A3B346B`.

## Caller-owned storage

`BulkLoad` already knows the batch count and sizes its temporary arrays accordingly. An optional `BulkLoadWorkspace` now retains the integer sort order and two double coordinate arrays across successive builds. It requires about 20 bytes per reserved entry, plus array headers. The caller must not share one workspace across concurrent builds.

Independent repeat, mean ± sample standard deviation per build:

| Entries | Default | Reused workspace | Default allocation | Reused allocation |
|---:|---:|---:|---:|---:|
| 1,000 | 65.25 ± 0.92 µs | 63.02 ± 0.11 µs | 133.71 KB | 112.66 KB |
| 10,000 | 1,806.46 ± 20.88 µs | 1,800.32 ± 8.59 µs | 1,308.32 KB | 1,099.67 KB |

The first run gave inconsistent 1,000-entry timing; both exports are retained as [first](results/hypotheses/workspace.csv) and [repeat](results/hypotheses/workspace-repeat.csv). The repeat establishes an allocation saving of about 21 KB and 209 KB per build, with no material time change. A newly allocated workspace gives no comparable allocation saving because its own arrays must be charged. **Retained as an optional allocation-control API**, not as a build-speed claim. Retained scratch memory and the caller's initial allocation are excluded from the reused-build allocation column.

Pre-sizing every newly created result list to the entire index is costly for the mixed fixture:

| Entries | Default new list | New list at entry-count capacity | Reused caller list |
|---:|---:|---:|---:|
| 1,000 | 5.79 µs / 4,272 B | 19.66 µs / 259,584 B | 5.00 µs / 0 B |
| 10,000 | 24.58 µs / 16,112 B | 94.48 µs / 2,563,584 B | 14.44 µs / 0 B |

Times are per 64-query batch. A reused list has a different ownership contract: callers cannot retain its contents across subsequent searches without copying. **Use the existing `Search(bounds, results)` API when reuse is acceptable.** [Raw result](results/hypotheses/output.csv).

## Four-entry query cache

The tested cache retains complete results for four exact query rectangles and invalidates them on insertion. A cache of four individual items alone cannot answer an intersection query: uncached items may also intersect. The result cache showed the expected hit-rate tradeoff:

| Entries | Query pattern | Packed tree | Four-result cache |
|---:|---|---:|---:|
| 1,000 | Four exact windows repeated | 3.25 µs | 0.53 µs |
| 1,000 | 64 distinct windows | 4.81 µs | 5.71 µs |
| 10,000 | Four exact windows repeated | 6.12 µs | 0.53 µs |
| 10,000 | 64 distinct windows | 14.43 µs | 16.97 µs |

Times are per batch of 64 queries. The cache copies values into the caller's result list; cached lists retain memory. The 10,000-entry distinct-window cache result was noisy (sample standard deviation 2.37 µs). **Not integrated:** there is no established exact-repeat workload or acceptable miss penalty for the library's general API. [Raw result](results/hypotheses/cache.csv).

## SIMD, byte spans, and brute-force scanning

The linear candidate stores four double coordinate columns and writes matching IDs to the same kind of result list as the tree. A `Vector256<double>` comparison produces four lane masks, which are ANDed and enumerated with `TrailingZeroCount`. It has a scalar tail and fallback. The four-separate-bitmap version writes four `ulong[]` buffers before merging; the later one-word version combines matches into one 64-bit word per block and enumerates that word.

Representative 64-query results, mean ± sample standard deviation:

| Entries | Query | Packed tree | One-word SIMD scan | Interpretation |
|---:|---|---:|---:|---|
| 32 | Broad, width 1,000 | 3.290 ± 0.006 µs | 1.692 ± 0.005 µs | Scan faster |
| 256 | Broad, width 1,000 | 17.059 ± 0.029 µs | 11.088 ± 0.023 µs | Scan faster |
| 10,000 | Broad, width 1,000 | 560.196 ± 2.352 µs | 496.595 ± 1.402 µs | Scan faster |
| 10,000 | Points | 5.788 ± 0.048 µs | 223.486 ± 4.101 µs | Tree much faster |

The 10,000-entry broad result repeated at 561.93 versus 494.11 µs in the width sweep. At 10,000 entries, width 20 was 10.09 versus 301.13 µs, width 200 was 146.58 versus 392.86 µs, and width 500 was 595.66 versus 413.19 µs, tree then scan respectively. The crossover is workload-specific; the 1,000-entry broad result changed direction across independent fixture classes, so it is **inconclusive**. [Initial scan](results/hypotheses/scan.csv), [one-word comparison](results/hypotheses/onebitmap.csv), [width sweep](results/hypotheses/crossover.csv).

The flat index builds much faster than a packed R-tree because it only copies coordinates; at 10,000 entries it took 44.66 ± 4.68 µs and allocated 317.68 KB, versus 2,312.69 ± 21.87 µs and 1,308.32 KB for the packed tree. This is a different index with no efficient incremental insertion or spatial pruning. It is attractive for a static, small or broad-query workload; it is not a replacement for selective intersection searches. [Raw build result](results/hypotheses/build.csv).

The byte-span variant uses `MemoryMarshal.Cast<byte, double>` to create four views over caller-owned bytes. The cast does not copy geometry. It requires numeric, reference-free storage; arbitrary managed `T` values and the current node objects cannot reside in that byte span. A borrowed span also cannot be retained in this heap-allocated mutable tree without a different lifetime design. Both ordinary and deliberately one-byte-offset spans returned correct results. The clean 10,000-entry point batch took 352.27 µs with indexed arrays, 260.70 µs with GC-tracked byrefs to those arrays, and 238.54 µs with the byte span. For broad queries the same methods took 1,476.41, 1,491.71, and 1,554.12 µs. **No universal byte-span or alignment advantage was established.** [Initial byte-span comparison](results/hypotheses/bytes.csv), [clean byref comparison](results/hypotheses/byref-clean.csv).

An optimized diagnostic disassembly of the SIMD loop contains `vmovups`, `vcmplepd`, `vcmpgepd`, `vandpd`, `vmovmskpd`, and `tzcnt`. The indexed-array version has four array range checks in the vector loop. The managed-byref and byte-span versions load through validated loop bounds without those per-array checks. `vmovups` is an unaligned load, so a 32-byte-aligned allocation is not required for this implementation. This is a generated-code observation, not a hardware-counter attribution. The diagnostic used `DOTNET_JitDisasm` and disabled tiering to obtain one optimized listing; acceptance timings used the default benchmark runtime settings.

**Decision:** keep the scalar, SIMD, bitmap, and byte-span variants as benchmark experiments. The one-word scan wins on the measured broad windows but loses decisively on selective queries. Integrating a flat index or an automatic switch into the mutable R-tree would add storage and update cost, and no representative query mix has been specified to justify that tradeoff.

## Focused candidate ledger

| Catalogue area | Candidate and disposition |
|---|---|
| M1, M7 | Reusable bulk scratch: retained optional API for lower repeated allocation. Full-capacity new result list: rejected. Reused caller list: existing API, confirmed. |
| M5, M6 | Flat coordinate columns and byte-span layout: tested. Deliberately unaligned access is correct; alignment speed effect is mixed. No node-layout rewrite retained. |
| C3, C4 | Four-lane comparisons, mask extraction, bit enumeration: tested. One-word compaction improves broad scans. Selective queries reject a general replacement. |
| S1 | Four materialized bitmaps: tested; extra bitmap traffic gave no robust advantage. One local bitmap word: retained in the benchmark rig. |
| S4 | Four exact-query results: tested; repeat benefit and distinct-query penalty measured. No general cache retained. |

The remaining catalogue areas and earlier experiments are recorded in [PERFORMANCE.md](PERFORMANCE.md). No concurrency or persistent raw-pointer optimization is introduced by these candidates.
