```

BenchmarkDotNet v0.15.8, Windows 11 (10.0.26200.9457/25H2/2025Update/HudsonValley2)
AMD Ryzen 9 5950X 3.40GHz, 1 CPU, 32 logical and 16 physical cores
.NET SDK 10.0.401
  [Host]   : .NET 10.0.12 (10.0.12, 10.0.1226.42308), X64 RyuJIT x86-64-v3
  ShortRun : .NET 10.0.12 (10.0.12, 10.0.1226.42308), X64 RyuJIT x86-64-v3

Job=ShortRun  IterationCount=3  LaunchCount=1  
WarmupCount=3  

```
| Method | Shape | Mean         | Error        | StdDev      | Ratio | RatioSD | Allocated | Alloc Ratio |
|------- |------ |-------------:|-------------:|------------:|------:|--------:|----------:|------------:|
| **Before** | **All**   | **2,362.805 μs** | **8,332.118 μs** | **456.7115 μs** |  **1.03** |    **0.25** |         **-** |          **NA** |
| After  | All   | 1,315.097 μs | 1,375.869 μs |  75.4160 μs |  0.57 |    0.10 |         - |          NA |
|        |       |              |              |             |       |         |           |             |
| **Before** | **Broad** |   **751.619 μs** |   **101.034 μs** |   **5.5380 μs** |  **1.00** |    **0.01** |         **-** |          **NA** |
| After  | Broad |   483.935 μs |   262.504 μs |  14.3887 μs |  0.64 |    0.02 |         - |          NA |
|        |       |              |              |             |       |         |           |             |
| **Before** | **Point** |     **7.905 μs** |     **2.457 μs** |   **0.1347 μs** |  **1.00** |    **0.02** |         **-** |          **NA** |
| After  | Point |     7.590 μs |     5.421 μs |   0.2971 μs |  0.96 |    0.04 |         - |          NA |
