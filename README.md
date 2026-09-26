# Tedd.RTree

A mutable, two-dimensional R-tree for .NET 10. It indexes axis-aligned rectangles and returns items whose bounds intersect a query rectangle. Boundary contact counts as intersection.

[Documentation, examples, and benchmark comparison](https://tedd.github.io/Tedd.RTree/).

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

`Search` appends to the supplied list and returns the number appended. `Search(bounds)` creates and returns a list. Result order is unspecified. Entries may have duplicate bounds or values. Coordinates must be finite and ordered. `Clear` discards the index. `BulkLoad` uses Sort-Tile-Recursive packing on an empty tree; later individual inserts are supported. The tree has no deletion API. It is not safe to mutate concurrently or during a search.

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

Local measurements, optimization decisions, and raw exports are in [the performance record](benchmarks/PERFORMANCE.md).
