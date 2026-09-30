# Tedd.RTree

A mutable 2D and 3D R-tree library for .NET 10. It indexes axis-aligned rectangles or boxes and returns items whose bounds intersect a query. Boundary contact counts as intersection.

[Documentation, examples, and benchmark comparison](https://tedd.no/Tedd.RTree/).

Install from [NuGet](https://www.nuget.org/packages/Tedd.RTree) in a .NET 10 project:

```powershell
dotnet add package Tedd.RTree
```

```csharp
using Tedd.RTree;

var tree = new RTree<string>(maxEntries: 16);
tree.Insert(new Rectangle(0, 0, 10, 10), "A");

var results = new List<string>();
int added = tree.Search(new Rectangle(5, 5, 20, 20), results);

var packed = new RTree<string>();
packed.BulkLoad(new[]
{
    new SpatialEntry<string>(new Rectangle(0, 0, 10, 10), "A"),
    new SpatialEntry<string>(new Rectangle(20, 20, 30, 30), "B")
});
```

`Search` appends to the supplied list and returns the number appended. `Search(bounds)` creates and returns a list. Result order is unspecified. Entries may have duplicate bounds or values. Coordinates must be finite and ordered. `Clear` discards the index. `BulkLoad` uses Sort-Tile-Recursive packing on an empty tree; later individual inserts, removals, and moves are supported. `Remove(bounds, item)` removes one matching entry; `Update(oldBounds, item, newBounds)` moves one matching entry. Concurrent searches on an unchanged tree are safe when each search uses its own result list. Mutation during a search is not safe.

## Batch searches

`SearchBatch` accepts query bounds, one caller-owned result list per query, and a count buffer with at least one slot per query. It appends matches to each list, writes the number appended for each query, and returns the total as a `long`. Existing list contents and unused count slots are preserved. Empty batches return zero. Invalid buffer lengths or null result lists are rejected before output is changed.

```csharp
Rectangle[] queries = [new(0, 0, 10, 10), new(20, 20, 30, 30)];
List<string>[] matches = [new(), new()];
int[] counts = new int[queries.Length];
long total = packed.SearchBatch(queries, matches, counts);
```

The same method is available on the coordinate-generic 2D and 3D trees and their concurrent and snapshot variants. A concurrent batch holds one read lock for its entire duration; writers wait until it completes. A snapshot batch uses one published tree for every query, even during replacement. Batches run sequentially. Clear the result lists before reusing them when only the latest matches are needed. Concurrent batches must own separate output storage, and query inputs must remain unchanged while a batch runs. `BulkLoad` handles initial batch construction; `ReplaceAll` handles complete batch replacement on snapshot indexes.

## Coordinate types and 3D bounds

The original `Rectangle`, `RTree<T>`, `SnapshotRTree<T>`, and `ConcurrentRTree<T>` APIs remain available for two-dimensional `double` coordinates. The coordinate-generic 2D APIs use `Rectangle2D<TCoordinate>`, `RTree2D<TCoordinate, T>`, `SnapshotRTree2D<TCoordinate, T>`, and `ConcurrentRTree2D<TCoordinate, T>`. The corresponding 3D APIs use `Box<TCoordinate>`, `RTree3D<TCoordinate, T>`, `SnapshotRTree3D<TCoordinate, T>`, and `ConcurrentRTree3D<TCoordinate, T>`. Bulk loading accepts `SpatialEntry2D<TCoordinate, T>` in 2D and `SpatialEntry3D<TCoordinate, T>` in 3D. Both dimensions accept a `BulkLoadWorkspace` for reusable sorting scratch.

```csharp
var voxels = new RTree3D<int, int>();
voxels.Insert(new Box<int>(10, 20, 30, 10, 20, 30), item: 42);
List<int> atVoxel = voxels.Search(new Box<int>(10, 20, 30, 10, 20, 30));

var largeWorld = new RTree3D<long, string>();
largeWorld.Insert(new Box<long>(9_007_199_254_740_993, 0, 0,
                               9_007_199_254_740_993, 0, 0), "origin");
```

Bounds include their edges and faces. Represent a single voxel position with equal minimum and maximum coordinates, as above. Unit boxes specified as `[x, x + 1]` touch their neighbors and therefore intersect under this API. `int` and `long` searches, node metrics, and bulk-load sort keys use exact integer arithmetic; integer bounds are never converted to floating point. `float` and `double` use floating-point metrics. Integer node construction uses `BigInteger` for overflow-safe area and volume calculations, so smaller bounds can improve query memory use while making bulk construction costlier. Measure the intended build-to-query ratio before selecting a coordinate type for speed alone.

For repeated bulk builds from a `SpatialEntry<int>[] entries` batch, a caller can reuse sorting scratch without changing result semantics:

```csharp
var workspace = new BulkLoadWorkspace(capacity: entries.Length);
var tree = new RTree<int>();
tree.BulkLoad(entries, workspace);
```

For the original 2D `double` tree, the workspace retains approximately 20 bytes per reserved entry in three primitive arrays. Generic integer builds retain additional exact sort keys; 3D builds retain a third coordinate axis. Do not use one workspace concurrently for multiple builds. It reduces repeated allocation; the measured build time of the original tree did not materially change. A caller-owned result list can likewise be reused across searches with `Search(bounds, results)`.

## Concurrent access

For regular updates to most entries, publish a complete batch of current positions. Each search uses one complete version while the next tree is built:

```csharp
var index = new SnapshotRTree<int>();
index.ReplaceAll(new[]
{
    new SpatialEntry<int>(new Rectangle(0, 0, 10, 10), 42)
});
List<int> matches = index.Search(new Rectangle(5, 5, 6, 6));
```

When each move must be visible immediately, use stable, unique values as keys:

```csharp
using var index = new ConcurrentRTree<int>();
index.Add(new Rectangle(0, 0, 10, 10), 42);
index.Move(42, new Rectangle(20, 20, 30, 30));
```

`ConcurrentRTree<T>` serializes changes and protects searches with a reader/writer lock. At 10,000 entries, moving 100 or 1,000 entries was cheaper than rebuilding; moving all 10,000 was substantially dearer. The two APIs have distinct visibility contracts. Every concurrent search needs its own result list. See [concurrency measurements](https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CONCURRENCY.md).

## Build and validation

```powershell
dotnet build Tedd.RTree.sln -c Release
dotnet run --project tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj -c Release
```

The differential test compares searches with a linear scan across several node capacities, randomized insertion sequences, duplicate rectangles, edge contacts, and clearing/reuse.

## Benchmarks

```powershell
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release -- --filter '*SpatialBenchmarks*'
```

The BenchmarkDotNet project compares sequential construction, bulk loading, and 64 intersection queries with [RBush 4.0.0](https://www.nuget.org/packages/RBush/4.0.0) and [NetTopologySuite STRtree 2.6.0](https://www.nuget.org/packages/NetTopologySuite/2.6.0). Fixtures use fixed seeds, 1,000 and 10,000 entries, and uniform and clustered placements. Query windows range from point searches to broad regions. Fixture and adapter objects are prepared outside timing. Construction includes all insertions or bulk loading, and STRtree's explicit `Build`. Queries run against prepared indexes and consume every match. Both reused-list and allocating query paths are measured for Tedd.RTree. `GlobalSetup` verifies each adapter's result count against a linear scan before measuring.

STRtree is a packed, query-focused index that stops accepting inserts after build. Its construction and query results should be interpreted together for read-heavy use; it is not interchangeable with a mutable tree.

Local measurements, optimization decisions, and raw exports are in [the performance record](https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/PERFORMANCE.md).

Follow-up tests of caller-owned scratch, query caching, SIMD scans, and bitmap compaction are in [the hypothesis record](https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/HYPOTHESES.md).
