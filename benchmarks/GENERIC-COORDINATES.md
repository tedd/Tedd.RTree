# Numeric coordinate and voxel benchmark

The numeric indexes are `RTree2D<TCoordinate, T>` and `RTree3D<TCoordinate, T>`. The original `RTree<T>` provides a 2D `double` reference. For `int` and `long`, query comparisons, node metrics, and bulk-load sort keys remain exact. Integer construction uses `BigInteger` where differences, areas, or volumes can exceed the coordinate type.

## Reproduce

```powershell
dotnet build Tedd.RTree.sln -c Release
dotnet run --project tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj -c Release --no-build
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*VoxelCoordinateBenchmarks*'
dotnet run --project benchmarks/Tedd.RTree.Benchmarks/Tedd.RTree.Benchmarks.csproj -c Release --no-build -- --filter '*VoxelBuildBenchmarks*'
```

The fixture in [VoxelCoordinateBenchmarks.cs](Tedd.RTree.Benchmarks/VoxelCoordinateBenchmarks.cs) prepares 10,000 unit bounds from seed 73211, node capacity 16, and 64 reused-list queries. The same integer-valued positions are used for every coordinate type. Point windows have zero width; region windows have width 100. Each build benchmark creates and packs a fresh index from prepared entries. Query setup checks equal result counts across types; the differential test suite checks exact result sets against linear scans. Query timing excludes tree construction and allocates no managed memory in the measured operation.

The index source was release commit `8fd12a6`; the benchmark fixture was prepared for this results commit. The local machine was Windows 11, AMD Ryzen 9 5950X, .NET 10.0.12 x64 RyuJIT, SDK 10.0.401, BenchmarkDotNet 0.15.8. No CPU affinity or power-policy control was imposed. Query benchmarks used one launch, five warmups, and ten measured iterations; builds used one launch, three warmups, and five measured iterations. Results are local estimates, not cross-machine guarantees.

## Query results

Mean ± sample standard deviation per batch of 64 queries:

| Dimension | Coordinate | Point | Region |
|---|---|---:|---:|
| 2D | Original `double` | 8.34 ± 0.32 µs | 47.27 ± 3.30 µs |
| 2D | `int` | 7.85 ± 0.25 µs | 40.26 ± 2.61 µs |
| 2D | `long` | 7.64 ± 0.57 µs | 49.07 ± 14.98 µs |
| 2D | `float` | 7.69 ± 0.77 µs | 38.27 ± 1.32 µs |
| 2D | Generic `double` | 6.65 ± 0.44 µs | 52.48 ± 3.19 µs |
| 3D | `int` | 7.82 ± 0.36 µs | 20.90 ± 1.67 µs |
| 3D | `long` | 9.21 ± 1.42 µs | 24.32 ± 3.29 µs |
| 3D | `float` | 11.43 ± 0.32 µs | 28.98 ± 5.12 µs |
| 3D | `double` | 12.57 ± 0.31 µs | 22.99 ± 1.12 µs |

The 2D `int` region mean was 23% below generic `double`; the 3D `int` region mean was 9% below `double`. These figures include differences in index layout and tree shape, and do not isolate numeric comparison instructions. Query means shifted materially between rounds on this uncontrolled machine; 2D `long` region queries were especially variable. [Release query CSV](results/generic-coordinates/query-release.csv) contains all cases, unrounded estimates, and outlier notes. Earlier [short](results/generic-coordinates/query-short.csv) and [focused](results/generic-coordinates/query-repeat.csv) runs provide a view of run-to-run variation.

## Build results

Mean ± sample standard deviation and managed allocation per complete 10,000-entry build:

| Dimension | Coordinate | Time | Allocated |
|---|---|---:|---:|
| 2D | Original `double` | 1.992 ± 0.066 ms | 1,309 KB |
| 2D | `int` | 2.366 ± 0.070 ms | 1,120 KB |
| 2D | `long` | 2.383 ± 0.040 ms | 1,475 KB |
| 2D | `float` | 1.974 ± 0.099 ms | 953 KB |
| 2D | Generic `double` | 2.059 ± 0.044 ms | 1,309 KB |
| 3D | `int` | 3.467 ± 0.093 ms | 1,469 KB |
| 3D | `long` | 3.680 ± 0.045 ms | 2,002 KB |
| 3D | `float` | 2.700 ± 0.068 ms | 1,219 KB |
| 3D | `double` | 2.822 ± 0.069 ms | 1,752 KB |

In 3D, integer builds were slower than `double` on this fixture; `int` allocated fewer bytes while `long` allocated more. The 2D integer build means were also above `double` in this round, unlike an earlier short run. [Release build CSV](results/generic-coordinates/build-release.csv) contains unrounded estimates and GC counts; the [earlier build CSV](results/generic-coordinates/build-short.csv) shows run-to-run variation. These measurements exclude entry-array preparation and repeated updates.

## Decision and limits

`int` and `long` provide exact integer coordinates. `float` and `double` cannot represent every integer beyond 2^24 and 2^53 respectively. On this fixture, `int` reduced region-query mean and build allocation relative to generic `double`, while integer construction cost increased. Run-to-run variation limits fine-grained rankings, especially for point searches. Other world distributions, update rates, and query widths can change the result; selecting a coordinate type solely for throughput requires an application-level measurement.

The relevant optimization catalogue paths were coordinate storage/layout (M5), sorting scratch and allocation (M1/M7), spatial predicate branches (C2), and generic value-type specialization (R2). The fixture measured complete search and build operations, rather than a synthetic comparison loop. No new SIMD, unsafe indexing, hash lookup, or concurrency algorithm was introduced. Existing broader [performance](PERFORMANCE.md) and [hypothesis](HYPOTHESES.md) records cover those unrelated candidates for the original 2D tree.
