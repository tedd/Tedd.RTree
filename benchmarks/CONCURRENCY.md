# Concurrency and moving-entry measurements

## Reproduce

```powershell
dotnet build Tedd.RTree.sln -c Release
dotnet run --project tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj -c Release --no-build
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*ParallelSearchBenchmarks*' '*ShardedSearchBenchmarks*' '*SearchWrapperBenchmarks*' '*MovingUpdateBenchmarks*'
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --probe-concurrency
```

The fixture code is in [ConcurrencyBenchmarks.cs](Tedd.RTree.Benchmarks/ConcurrencyBenchmarks.cs) and [ConcurrencyProbe.cs](Tedd.RTree.Benchmarks/ConcurrencyProbe.cs). The starting repository commit was `b5158be`. BenchmarkDotNet 0.15.8 used .NET 10.0.12 x64 RyuJIT x86-64-v3, AMD Ryzen 9 5950X, Windows 11 10.0.26200, one launch, three warmups, and three measured iterations. The GC was concurrent workstation. Timed runs were serialized. No affinity was pinned. Values below are local observations, not a general throughput guarantee.

The fixture has 10,000 uniformly placed 1–5 unit rectangles in a 1,000 × 1,000 region, seed 73211, and node capacity 16. Point queries have zero width; broad queries have width 1,000. Each method returns or consumes the result count. Worker-local lists keep output ownership independent. Setup checks result equivalence before timing. The sharded single-query fixture uses one fixed window beginning at (250, 250); its absolute times should be compared within that fixture only.

## Parallel search

Splitting one query over four separately built 2,500-entry trees adds scheduling and merging. The direct 10,000-entry tree was faster on both tested windows:

| Single query | Direct tree | Four shards, serial | Four shards, parallel |
|---|---:|---:|---:|
| Point | 0.051 ± 0.001 µs | 0.185 ± 0.003 µs | 1.946 ± 0.035 µs |
| Broad | 17.733 ± 0.172 µs | 17.714 ± 0.048 µs | 26.824 ± 0.131 µs |

The parallel form allocated about 1.9–2.1 KB per query. A separate one-query dispatch control took 0.050 µs directly and 1.45–2.03 µs through `Parallel.For` for a point query; only one worker performed useful work in that control. These results reject per-query parallel dispatch for the tested 10,000-entry searches. [Sharded raw data](results/concurrency/shards.csv), [dispatch control](results/concurrency/parallel-single.csv).

Independent queries can be divided among existing workers, with one result list per worker. Each invocation of this benchmark dispatches one batch to four or eight workers:

| Batch | Sequential | Four workers | Eight workers |
|---|---:|---:|---:|
| 64 point queries | 5.811 ± 0.007 µs | 5.474 ± 0.117 µs | 6.559 ± 0.035 µs |
| 1,024 point queries | 235.765 ± 2.157 µs | 113.693 ± 6.883 µs | 77.155 ± 8.745 µs |
| 64 broad queries | 561.282 ± 1.517 µs | 936.477 ± 10.911 µs | 806.276 ± 3.279 µs |
| 1,024 broad queries | 9,343.461 ± 30.364 µs | 15,353.398 ± 191.290 µs | 11,747.666 ± 52.183 µs |

At 1,024 selective queries, eight workers gave about three times the sequential throughput. The broad-query batch regressed on this machine; the cause was not isolated with hardware counters. There is no general parallel-search switch in the library. Applications with many independent queries can schedule coarse batches themselves. [Raw batch data](results/concurrency/parallel-batches.csv).

## Two update contracts

`SnapshotRTree<T>` builds a new packed tree under a writer-only lock and publishes its reference with `Volatile.Write`. Each search takes one reference with `Volatile.Read` and traverses that version. A search started before publication may finish on the previous version. Readers do not wait for the rebuild. Old versions remain allocated until their readers finish and the GC reclaims them. Concurrent writers serialize. The caller must keep the input batch unchanged during `ReplaceAll`.

`ConcurrentRTree<T>` requires unique, stable values as keys. A `ReaderWriterLockSlim` protects the location map and mutable tree. `Move` removes and reinserts one entry, then returns after the new bounds are visible. Existing searches hold the read lock until completion, so a writer may wait. The underlying `RTree<T>` now provides `Remove(bounds, item)` and `Update(oldBounds, item, newBounds)`; it remains unsynchronized for callers that want to manage their own access. Both concurrent APIs require a separate result list for each simultaneous search.

Uncontended search overhead for 64 queries:

| Queries | Direct tree | Published snapshot | Reader/writer lock |
|---|---:|---:|---:|
| Point | 5.831 ± 0.018 µs | 6.028 ± 0.056 µs | 6.728 ± 0.014 µs |
| Broad | 550.468 ± 2.451 µs | 552.350 ± 0.618 µs | 555.923 ± 1.624 µs |

The snapshot wrapper added about 3% to point-search time in this fixture; the reader/writer lock added about 15%. Both changes were below 1% for broad queries. [Raw search data](results/concurrency/wrappers.csv).

Update cost, alternating two prepared sets of bounds at 10,000 total entries:

| Entries moved | Publish complete snapshot | Move each immediately |
|---:|---:|---:|
| 100 | 1.856 ± 0.006 ms / 1,100 KB | 0.061 ± 0.008 ms / 4 KB |
| 1,000 | 1.873 ± 0.019 ms / 1,100 KB | 0.756 ± 0.012 ms / 33 KB |
| 10,000 | 1.753 ± 0.011 ms / 1,100 KB | 14.768 ± 0.078 ms / 2,346 KB |

These are update-only times without readers. Snapshot rebuild has essentially fixed work for 10,000 total entries; the mutable path pays for each move and structural repair. The mutable benchmark alternates positions over repeated calls, so its tree evolves naturally during measurement. For most entries moving, snapshot replacement is about 8.4 times faster and allocates less in this fixture. At sparse update counts, immediate moves are cheaper. The data bracket a workload-specific crossover between 1,000 and 10,000 moves; they do not locate it precisely. Reusing deletion scratch reduced allocation at 10,000 moves from 3,764 KB to 2,346 KB, with no material time change. A 60 Hz replacement rate would allocate about 64 MiB/s for the index alone; preparing a new input batch adds its own cost. [Original update run](results/concurrency/moves.csv), [retained scratch run](results/concurrency/moves-scratch.csv).

## Readers while most entries move

The sustained probe runs four dedicated search threads for two seconds. A writer alternates full 10,000-entry batches, sleeping 10 ms after each update; the measured frame count is the actual achieved rate. Search latency is sampled once per 64 calls. These runs include thread contention, allocation, GC, and new-tree cache turnover. Their short duration and varying machine state make precise throughput ratios provisional.

Across the two runs on the retained code, the snapshot writer completed 125–132 replacements in two seconds. The immediate writer completed 9–15 full sets of individual moves while readers were active. Snapshot point searches had sampled p99 latency of 0.3–0.4 µs; immediate point searches had p99 of 40.1–41.8 µs. For broad searches, snapshot p99 was 34.1–84.2 µs and immediate p99 was 132.5–158 µs. Broad-query throughput under snapshot replacement was lower than for an unchanged tree, even though searches took no lock. Its magnitude varied substantially between runs. The test does not isolate CPU contention from cache and GC effects. [Retained-code run 1](results/concurrency/sustained-scratch-1.csv), [run 2](results/concurrency/sustained-scratch-2.csv). [Earlier run 1](results/concurrency/sustained-1.csv) and [run 2](results/concurrency/sustained-2.csv) preceded the deletion-scratch change.

## Decision and candidate ledger

| Area | Tested candidate | Disposition |
|---|---|---|
| T1, worker ownership | Worker-local result lists and counters | Retained in benchmarks; no shared writable search state was introduced. False-sharing padding has no identified hot shared field. |
| T2, ownership and publication | Immutable published tree versus a locked mutable tree | Both retained as separate APIs. Snapshot publication serves frequent whole-batch movement; immediate moves serve sparse changes or strict per-move visibility. |
| T3, locking | `ReaderWriterLockSlim` around mutation and searches | Retained for immediate mode. It adds point-search overhead and can substantially delay updates under sustained readers. |
| T4, scheduling | One-query dispatch, four sharded trees, and coarse independent-query batches | Per-query parallelization rejected at 10,000 entries. Coarse point-query batches can gain throughput; broad batches regressed on this machine. |
| M1, mutation scratch | Reuse the deletion reinsertion list | Retained for lower allocation; 10,000 moves allocated 2,346 KB instead of 3,764 KB. |

Search and update must be assessed together. A published snapshot gives each search one coherent frame, whereas the immediate index can expose successive individual moves from a frame. Neither API can make a mutable value object itself thread-safe; only indexed bounds and membership are controlled here.
