# R-tree NuGet package comparison

The [website comparison](https://tedd.github.io/Tedd.RTree/#benchmarks) measures five packages that pass identical intersection-result checks. Build throughput is entries per second; query throughput is windows per second. The tables report elapsed time and allocation for the same operations. Lower elapsed time is better; higher throughput is better.

## Packages and construction

| Package | Version | Construction | Coordinates | Node capacity |
|---|---|---|---|---:|
| Tedd.RTree | Repository source | STR bulk load | 2D double | 16 |
| [RBush](https://www.nuget.org/packages/RBush/4.0.0) | 4.0.0 | BulkLoad | 2D double | 16 |
| [NetTopologySuite](https://www.nuget.org/packages/NetTopologySuite/2.6.0) | 2.6.0 | STRtree insert batch + Build | 2D double | 16 |
| [RTree](https://www.nuget.org/packages/RTree/1.1.0) | 1.1.0 | Incremental Add | 3D float, z = 0 | 16, minimum 6 |
| [Enyim.Collections.RTree](https://www.nuget.org/packages/Enyim.Collections.RTree/1.0.5) | 1.0.5 | Load | 2D int | 16 |
| [SharpTrees](https://www.nuget.org/packages/SharpTrees/1.0.6) | 1.0.6 | Incremental Add; excluded after validation failure | 2D double | 4, minimum 2, Exhaustive |

RTree 1.1.0 indexes three dimensions; setting both z bounds to zero preserves the fixture's 2D intersection predicate. Enyim accepts integer envelopes. The shared fixture therefore uses small integer-valued positions and dimensions, represented exactly in every adapter. This is a comparison of available APIs on one shared workload, not an isolated comparison of algorithms or coordinate types. RTree's incremental construction cannot be interpreted as a bulk-loader result. STRtree is packed and stops accepting inserts after building.

Enyim and SharpTrees target .NET Framework, so NuGet emits NU1701 compatibility warnings. The in-memory runtime checks establish the tested behavior on .NET 10, not general framework compatibility. BenchmarkDotNet reports that Enyim's released DLL has optimizations disabled. The runner permits that published binary and measures it as distributed; the benchmark host and Tedd.RTree are compiled in Release. No competitor was rebuilt or modified. The benchmark dependencies are not dependencies of the published Tedd.RTree package.

2D-RTree 1.0.1 was inspected but is not loaded into the shared benchmark process: it uses the same `RTree` assembly and namespace as RTree 1.1.0. Its integer API is not timed here.

## Method and validation

Measurement date: 30 September 2026. AMD Ryzen 9 5950X, Windows 11, .NET 10.0.12, SDK 10.0.401, BenchmarkDotNet 0.15.8. ShortRun uses one launch, three warm-ups, and three measured iterations. Means and sample standard deviations describe those three iterations; close differences and high-variance cases need longer runs on the target workload.

The seed is 73211. There are 1,000 or 10,000 rectangles. Uniform positions span a 1,000-unit square. Clustered positions occupy eight 30-unit regions separated by 125 units along both axes. Rectangle side lengths are integers from 1 through 5. Each operation queries the same 64 windows, alternating widths 0, 20, 200, and 1,000 units. Windows originate within the 1,000-unit square and may extend beyond it. Point queries, small regions, larger regions, and broad searches therefore all contribute to the aggregate query time.

Geometry, envelopes, item wrappers, and query inputs are prepared before timing. Every timed build creates a fresh tree and includes all native construction work. Enyim sorts its supplied list; each build includes a fresh copy so repeated builds do not receive an already sorted input. Query timing uses prepared trees and the native allocating collection APIs, consuming the result count. Tedd.RTree uses `Search(bounds)` rather than a reused list in this comparison. Query throughput counts windows, not matched items.

Every benchmark setup compares sorted result IDs with a brute-force inclusive intersection scan for all 64 queries. Equal counts alone are insufficient. The standalone validation command covers all four size/distribution combinations for each timed package, plus empty indexes, negative bounds, touching edges, identical rectangles with distinct IDs, disjoint windows, and reversed insertion order. CI runs that validation independently of the measurements.

```powershell
dotnet run --project benchmarks/Tedd.RTree.Benchmarks -c Release -- --validate-packages
dotnet run --project benchmarks/Tedd.RTree.Benchmarks -c Release -- --filter '*PackageComparisonBenchmarks*' --artifacts artifacts/package-comparison --exporters json
python benchmarks/update_package_comparison.py artifacts/package-comparison/results/PackageComparisonBenchmarks-report-full-compressed.json
```

The [fixture and adapters](Tedd.RTree.Benchmarks/PackageComparisonBenchmarks.cs) contain the exact generation and API paths. The generator updates the website charts, complete table, chart JSON, and this result table from a complete BenchmarkDotNet export. It rejects missing, duplicate, or unmeasured cases. [Raw CSV](results/package-comparison/PackageComparisonBenchmarks-report.csv), [full JSON](results/package-comparison/PackageComparisonBenchmarks-report-full-compressed.json), and [BenchmarkDotNet summary](results/package-comparison/PackageComparisonBenchmarks-report-github.md) retain the underlying evidence.

## Results

<!-- results:start -->

| Entries | Distribution | Operation | Package | Mean ± standard deviation | Allocated |
|---:|---|---|---|---:|---:|
| 1,000 | Clustered | Build | Enyim.Collections.RTree | 0.377 ± 0.004 ms | 68.11 KiB |
| 1,000 | Clustered | Build | NetTopologySuite | 0.364 ± 0.005 ms | 129.86 KiB |
| 1,000 | Clustered | Build | RBush | 0.325 ± 0.005 ms | 156.99 KiB |
| 1,000 | Clustered | Build | RTree | 0.618 ± 0.019 ms | 313.09 KiB |
| 1,000 | Clustered | Build | Tedd.RTree | 0.114 ± 0.003 ms | 133.72 KiB |
| 1,000 | Clustered | Query64 | Enyim.Collections.RTree | 1076.541 ± 18.530 µs | 129.25 KiB |
| 1,000 | Clustered | Query64 | NetTopologySuite | 84.799 ± 1.431 µs | 55.02 KiB |
| 1,000 | Clustered | Query64 | RBush | 75.435 ± 1.331 µs | 117.44 KiB |
| 1,000 | Clustered | Query64 | RTree | 114.663 ± 3.932 µs | 61.02 KiB |
| 1,000 | Clustered | Query64 | Tedd.RTree | 25.580 ± 1.622 µs | 55.02 KiB |
| 1,000 | Uniform | Build | Enyim.Collections.RTree | 0.401 ± 0.011 ms | 68.11 KiB |
| 1,000 | Uniform | Build | NetTopologySuite | 0.234 ± 0.049 ms | 129.86 KiB |
| 1,000 | Uniform | Build | RBush | 0.230 ± 0.001 ms | 156.99 KiB |
| 1,000 | Uniform | Build | RTree | 0.883 ± 0.025 ms | 314.43 KiB |
| 1,000 | Uniform | Build | Tedd.RTree | 0.123 ± 0.004 ms | 133.72 KiB |
| 1,000 | Uniform | Query64 | Enyim.Collections.RTree | 793.258 ± 61.230 µs | 116.62 KiB |
| 1,000 | Uniform | Query64 | NetTopologySuite | 68.640 ± 4.009 µs | 50.67 KiB |
| 1,000 | Uniform | Query64 | RBush | 81.347 ± 1.327 µs | 108.04 KiB |
| 1,000 | Uniform | Query64 | RTree | 120.743 ± 2.025 µs | 56.67 KiB |
| 1,000 | Uniform | Query64 | Tedd.RTree | 29.290 ± 3.099 µs | 50.67 KiB |
| 10,000 | Clustered | Build | Enyim.Collections.RTree | 5.657 ± 0.256 ms | 862.78 KiB |
| 10,000 | Clustered | Build | NetTopologySuite | 4.390 ± 0.011 ms | 1399.61 KiB |
| 10,000 | Clustered | Build | RBush | 5.803 ± 0.309 ms | 2165.52 KiB |
| 10,000 | Clustered | Build | RTree | 11.539 ± 0.247 ms | 3018.80 KiB |
| 10,000 | Clustered | Build | Tedd.RTree | 2.226 ± 0.046 ms | 1308.81 KiB |
| 10,000 | Clustered | Query64 | Enyim.Collections.RTree | 11627.599 ± 604.620 µs | 1297.76 KiB |
| 10,000 | Clustered | Query64 | NetTopologySuite | 1352.807 ± 84.770 µs | 634.80 KiB |
| 10,000 | Clustered | Query64 | RBush | 959.356 ± 21.793 µs | 1377.21 KiB |
| 10,000 | Clustered | Query64 | RTree | 1731.322 ± 49.235 µs | 640.80 KiB |
| 10,000 | Clustered | Query64 | Tedd.RTree | 197.635 ± 5.934 µs | 634.80 KiB |
| 10,000 | Uniform | Build | Enyim.Collections.RTree | 6.501 ± 0.376 ms | 862.78 KiB |
| 10,000 | Uniform | Build | NetTopologySuite | 4.959 ± 0.291 ms | 1399.61 KiB |
| 10,000 | Uniform | Build | RBush | 5.811 ± 0.126 ms | 2165.52 KiB |
| 10,000 | Uniform | Build | RTree | 11.937 ± 0.627 ms | 3023.33 KiB |
| 10,000 | Uniform | Build | Tedd.RTree | 2.153 ± 0.081 ms | 1308.81 KiB |
| 10,000 | Uniform | Query64 | Enyim.Collections.RTree | 11443.148 ± 210.574 µs | 1435.88 KiB |
| 10,000 | Uniform | Query64 | NetTopologySuite | 1777.963 ± 19.346 µs | 702.32 KiB |
| 10,000 | Uniform | Query64 | RBush | 1148.046 ± 34.031 µs | 1509.62 KiB |
| 10,000 | Uniform | Query64 | RTree | 2001.055 ± 104.507 µs | 708.32 KiB |
| 10,000 | Uniform | Query64 | Tedd.RTree | 253.936 ± 3.108 µs | 702.32 KiB |

<!-- results:end -->

## SharpTrees validation failure

SharpTrees 1.0.6 omits ID 942 on query 2 of the uniform 1,000-entry fixture: brute force returns 40 matches, and SharpTrees returns 39. This adapter uses unique item IDs, cached bounds, node maximum 4/minimum 2, and the package's Exhaustive split strategy. Bounds overlap checks include touching edges; the recorded failure concerns the tree's returned result set. No claim about its internal cause is made. Incorrect result sets are excluded from throughput ranking.

```powershell
dotnet run --project benchmarks/Tedd.RTree.Benchmarks -c Release -- --probe-sharptrees
```

This probe deliberately fails with a result-ID diagnostic. [Recorded output](results/package-comparison/sharptrees-validation.txt). SharpTrees remains a benchmark-project dependency so the failure can be reproduced using the published package. It is excluded from the timed parameter list and from the passing-package CI check.

## Scope

These figures do not measure deletion, moving entries, concurrent writers, larger datasets, non-integral coordinates, or real application distributions. The aggregate query benchmark mixes four window widths; it does not establish a ranking for each width separately. See [concurrent access measurements](CONCURRENCY.md) and [numeric coordinate measurements](GENERIC-COORDINATES.md) for separate fixtures.

Earlier [three-package measurements](PERFORMANCE.md) used a different double-valued fixture. Its original query-width expression lacked parentheses around `i % 4`, so the archived queries used widths 0 through 63 rather than the intended repeating four widths. Those historical query figures are not the current website comparison and should not be used as point/20/200/1,000-window evidence. The current fixtures explicitly parenthesize the selector.
