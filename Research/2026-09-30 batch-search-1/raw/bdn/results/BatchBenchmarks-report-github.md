```

BenchmarkDotNet v0.15.8, Windows 11 (10.0.26200.9457/25H2/2025Update/HudsonValley2)
AMD Ryzen 9 5950X 3.40GHz, 1 CPU, 32 logical and 16 physical cores
.NET SDK 10.0.401
  [Host]   : .NET 10.0.12 (10.0.12, 10.0.1226.42308), X64 RyuJIT x86-64-v3
  ShortRun : .NET 10.0.12 (10.0.12, 10.0.1226.42308), X64 RyuJIT x86-64-v3

Job=ShortRun  IterationCount=3  LaunchCount=1  
WarmupCount=3  

```
| Method            | Shape | Mean       | Error        | StdDev    | Ratio | RatioSD | Allocated | Alloc Ratio |
|------------------ |------ |-----------:|-------------:|----------:|------:|--------:|----------:|------------:|
| **ConcurrentSingles** | **Miss**  | **1,068.8 ns** |     **41.63 ns** |   **2.28 ns** |  **1.00** |    **0.00** |         **-** |          **NA** |
| ConcurrentBatch   | Miss  |   208.1 ns |    477.46 ns |  26.17 ns |  0.19 |    0.02 |         - |          NA |
| SnapshotSingles   | Miss  |   254.5 ns |      6.94 ns |   0.38 ns |  0.24 |    0.00 |         - |          NA |
| SnapshotBatch     | Miss  |   152.8 ns |     12.30 ns |   0.67 ns |  0.14 |    0.00 |         - |          NA |
|                   |       |            |              |           |       |         |           |             |
| **ConcurrentSingles** | **Point** | **9,156.0 ns** | **11,228.64 ns** | **615.48 ns** |  **1.00** |    **0.08** |         **-** |          **NA** |
| ConcurrentBatch   | Point | 7,580.7 ns |  7,711.29 ns | 422.68 ns |  0.83 |    0.06 |         - |          NA |
| SnapshotSingles   | Point | 7,246.8 ns |  2,940.83 ns | 161.20 ns |  0.79 |    0.05 |         - |          NA |
| SnapshotBatch     | Point | 5,554.2 ns |    167.50 ns |   9.18 ns |  0.61 |    0.04 |         - |          NA |
