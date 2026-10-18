# Generic 2D and 3D performance

Measured 18 October 2026: current source `cf34a58` against packed source `79a5dd2` (NuGet 1.0.12) in fresh matched processes. The implementation uses Hilbert ordering in 2D, three-axis Morton ordering in 3D, radix sorting and compact mutable nodes. Split/subtree metrics are reused; bounded integer products are exact, with BigInteger fallback for large extents. Individual updates retain remove/reinsert semantics and identical traversal fingerprints.

The 40 mutable configurations have current/1.0.12 update-time ratios of 0.423–0.699. Private bounds-union constructors are selectively inlined after generated-code inspection. These are complete 1,000-move batches, not individual latency percentiles. Construction, pre-update queries, post-update queries, allocation and every process range remain visible in the complete CSV and guardrail audit.

## Construction and queries

| API | Coordinates | Entries | Distribution | 1.0.12 build ms | Current build ms | 1.0.12 queries µs | Current queries µs |
|---|---|---:|---|---:|---:|---:|---:|
| 2D plain | double | 10,000 | clustered | 0.660 | 0.422 | 75.06 | 75.51 |
| 2D concurrent | double | 10,000 | uniform | 1.583 | 1.570 | 84.38 | 84.76 |
| 2D plain | double | 10,000 | uniform | 0.656 | 0.403 | 83.60 | 83.68 |
| 2D snapshot | double | 10,000 | uniform | 0.625 | 0.397 | 83.66 | 83.44 |
| 2D plain | double | 100,000 | clustered | 8.657 | 6.794 | 726.99 | 724.63 |
| 2D plain | double | 100,000 | uniform | 8.673 | 6.741 | 757.17 | 764.38 |
| 2D plain | float | 10,000 | clustered | 0.592 | 0.421 | 74.99 | 75.26 |
| 2D concurrent | float | 10,000 | uniform | 0.979 | 0.971 | 84.24 | 83.91 |
| 2D plain | float | 10,000 | uniform | 0.568 | 0.419 | 83.17 | 83.78 |
| 2D snapshot | float | 10,000 | uniform | 0.584 | 0.388 | 82.56 | 82.51 |
| 2D plain | float | 100,000 | clustered | 7.956 | 5.289 | 698.82 | 695.75 |
| 2D plain | float | 100,000 | uniform | 7.643 | 6.555 | 731.28 | 738.55 |
| 2D plain | int | 10,000 | clustered | 0.640 | 0.543 | 74.38 | 75.58 |
| 2D concurrent | int | 10,000 | uniform | 0.973 | 0.979 | 81.53 | 80.32 |
| 2D plain | int | 10,000 | uniform | 0.604 | 0.514 | 77.68 | 79.07 |
| 2D snapshot | int | 10,000 | uniform | 0.610 | 0.516 | 77.60 | 78.96 |
| 2D plain | int | 100,000 | clustered | 7.947 | 8.134 | 690.55 | 695.20 |
| 2D plain | int | 100,000 | uniform | 8.460 | 7.611 | 711.08 | 704.49 |
| 2D plain | long | 10,000 | clustered | 0.673 | 0.553 | 75.57 | 75.79 |
| 2D concurrent | long | 10,000 | uniform | 1.580 | 1.567 | 81.82 | 82.52 |
| 2D plain | long | 10,000 | uniform | 0.635 | 0.577 | 82.62 | 84.21 |
| 2D snapshot | long | 10,000 | uniform | 0.657 | 0.542 | 80.41 | 81.32 |
| 2D plain | long | 100,000 | clustered | 8.667 | 7.343 | 723.36 | 726.49 |
| 2D plain | long | 100,000 | uniform | 8.613 | 8.527 | 739.40 | 750.62 |
| 3D plain | double | 10,000 | clustered | 0.800 | 0.399 | 64.01 | 63.92 |
| 3D concurrent | double | 10,000 | uniform | 2.212 | 2.201 | 106.14 | 106.65 |
| 3D plain | double | 10,000 | uniform | 0.805 | 0.419 | 108.67 | 108.94 |
| 3D snapshot | double | 10,000 | uniform | 0.810 | 0.426 | 104.32 | 104.93 |
| 3D plain | double | 100,000 | clustered | 9.014 | 5.085 | 323.18 | 321.70 |
| 3D plain | double | 100,000 | uniform | 9.188 | 5.234 | 682.82 | 679.79 |
| 3D plain | float | 10,000 | clustered | 0.659 | 0.492 | 63.87 | 63.65 |
| 3D concurrent | float | 10,000 | uniform | 1.268 | 1.271 | 108.33 | 105.44 |
| 3D plain | float | 10,000 | uniform | 0.681 | 0.514 | 102.68 | 105.84 |
| 3D snapshot | float | 10,000 | uniform | 0.692 | 0.503 | 101.53 | 104.85 |
| 3D plain | float | 100,000 | clustered | 8.385 | 7.409 | 322.48 | 323.75 |
| 3D plain | float | 100,000 | uniform | 8.260 | 7.463 | 661.41 | 663.89 |
| 3D plain | int | 10,000 | clustered | 0.738 | 0.580 | 62.51 | 62.94 |
| 3D concurrent | int | 10,000 | uniform | 1.279 | 1.262 | 96.11 | 95.56 |
| 3D plain | int | 10,000 | uniform | 0.758 | 0.610 | 93.27 | 92.94 |
| 3D snapshot | int | 10,000 | uniform | 0.754 | 0.609 | 93.57 | 93.13 |
| 3D plain | int | 100,000 | clustered | 9.348 | 8.145 | 318.83 | 318.60 |
| 3D plain | int | 100,000 | uniform | 9.253 | 8.285 | 574.52 | 571.51 |
| 3D plain | long | 10,000 | clustered | 0.873 | 0.611 | 63.27 | 62.63 |
| 3D concurrent | long | 10,000 | uniform | 2.192 | 2.200 | 101.00 | 102.07 |
| 3D plain | long | 10,000 | uniform | 0.877 | 0.645 | 99.74 | 99.43 |
| 3D snapshot | long | 10,000 | uniform | 0.872 | 0.621 | 102.41 | 101.57 |
| 3D plain | long | 100,000 | clustered | 11.477 | 7.487 | 320.25 | 322.70 |
| 3D plain | long | 100,000 | uniform | 10.599 | 7.762 | 592.15 | 593.83 |

## Mutable update batches

| API | Coordinates | Entries | Distribution | 1.0.12 ms | Current ms | Current/1.0.12 | Post-update queries µs |
|---|---|---:|---|---:|---:|---:|---:|
| 2D plain | double | 10,000 | clustered | 7.838 | 4.326 | 0.552 | 91.97 |
| 2D concurrent | double | 10,000 | uniform | 9.109 | 5.125 | 0.563 | 109.65 |
| 2D plain | double | 10,000 | uniform | 8.731 | 5.063 | 0.580 | 108.06 |
| 2D plain | double | 100,000 | clustered | 13.026 | 7.868 | 0.604 | 921.74 |
| 2D plain | double | 100,000 | uniform | 24.419 | 13.310 | 0.545 | 1104.42 |
| 2D plain | float | 10,000 | clustered | 7.925 | 4.289 | 0.541 | 90.11 |
| 2D concurrent | float | 10,000 | uniform | 9.174 | 5.159 | 0.562 | 105.42 |
| 2D plain | float | 10,000 | uniform | 8.052 | 5.097 | 0.633 | 101.31 |
| 2D plain | float | 100,000 | clustered | 11.734 | 8.202 | 0.699 | 913.52 |
| 2D plain | float | 100,000 | uniform | 25.937 | 14.102 | 0.544 | 1030.00 |
| 2D plain | int | 10,000 | clustered | 28.294 | 14.307 | 0.506 | 91.36 |
| 2D concurrent | int | 10,000 | uniform | 31.332 | 15.718 | 0.502 | 106.67 |
| 2D plain | int | 10,000 | uniform | 31.047 | 15.759 | 0.508 | 100.04 |
| 2D plain | int | 100,000 | clustered | 41.567 | 23.027 | 0.554 | 909.94 |
| 2D plain | int | 100,000 | uniform | 96.468 | 48.798 | 0.506 | 1062.11 |
| 2D plain | long | 10,000 | clustered | 33.532 | 14.449 | 0.431 | 97.36 |
| 2D concurrent | long | 10,000 | uniform | 36.296 | 16.128 | 0.444 | 105.22 |
| 2D plain | long | 10,000 | uniform | 36.520 | 15.993 | 0.438 | 108.25 |
| 2D plain | long | 100,000 | clustered | 46.017 | 23.697 | 0.515 | 925.76 |
| 2D plain | long | 100,000 | uniform | 110.296 | 49.581 | 0.450 | 1086.86 |
| 3D plain | double | 10,000 | clustered | 11.351 | 6.991 | 0.616 | 81.10 |
| 3D concurrent | double | 10,000 | uniform | 9.898 | 5.412 | 0.547 | 127.08 |
| 3D plain | double | 10,000 | uniform | 9.943 | 5.369 | 0.540 | 125.80 |
| 3D plain | double | 100,000 | clustered | 16.093 | 9.961 | 0.619 | 403.94 |
| 3D plain | double | 100,000 | uniform | 23.179 | 12.070 | 0.521 | 914.86 |
| 3D plain | float | 10,000 | clustered | 11.631 | 6.609 | 0.568 | 76.70 |
| 3D concurrent | float | 10,000 | uniform | 9.586 | 5.177 | 0.540 | 120.94 |
| 3D plain | float | 10,000 | uniform | 9.591 | 5.013 | 0.523 | 123.29 |
| 3D plain | float | 100,000 | clustered | 16.135 | 10.024 | 0.621 | 406.42 |
| 3D plain | float | 100,000 | uniform | 21.908 | 11.460 | 0.523 | 861.78 |
| 3D plain | int | 10,000 | clustered | 40.901 | 17.821 | 0.436 | 77.17 |
| 3D concurrent | int | 10,000 | uniform | 36.394 | 15.618 | 0.429 | 115.91 |
| 3D plain | int | 10,000 | uniform | 36.416 | 15.421 | 0.423 | 112.36 |
| 3D plain | int | 100,000 | clustered | 54.243 | 26.005 | 0.479 | 400.21 |
| 3D plain | int | 100,000 | uniform | 86.945 | 37.417 | 0.430 | 767.75 |
| 3D plain | long | 10,000 | clustered | 42.857 | 18.816 | 0.439 | 78.04 |
| 3D concurrent | long | 10,000 | uniform | 36.193 | 16.320 | 0.451 | 120.97 |
| 3D plain | long | 10,000 | uniform | 36.895 | 16.234 | 0.440 | 121.90 |
| 3D plain | long | 100,000 | clustered | 54.837 | 26.449 | 0.482 | 389.13 |
| 3D plain | long | 100,000 | uniform | 86.613 | 38.843 | 0.448 | 780.16 |

## Guardrails and interpretation

The [guardrail audit](results/mutation-regressions/final/guardrails.csv) reports every current/1.0.12 median ratio and allocation counter, including failures of the prospective 5% elapsed threshold or exact allocation threshold. Read the [investigation report](../Research/2026-10-18-mutation-regressions/REPORT.md) for candidate disposition, contradictory observations, generated-code evidence and the acceptance decision. No flag is silently removed as noise.

All final construction and pre-update query medians remain within the 5% threshold. Two 2D int post-update query medians are 5.6% higher. A prospectively frozen [18-worker longer-window check](results/mutation-regressions/final-query-guard/summary.csv) gives candidate/control ratios of 1.046 and 1.010, with zero query allocation; its different preparation and composite windows cannot replace the original observations. A 0.3125-byte/build concurrent allocation-counter flag is also retained. Mutation and query allocations do not increase.

Earlier source epochs and every failed/inconclusive guardrail remain in the investigation record. The rejected leaf-contained replacement prototype changed later tree shape and regressed one post-update query aggregate by 18.9%. It is excluded. The integer exploration also observed one 12.4% post-query median discrepancy and a 4.5-byte/build allocation discrepancy; these remain retained separately from fresh confirmation.

## Method and limits

Ryzen 9 5950X, Windows 11, .NET SDK 10.0.402/runtime 10.0.13, Release x64 managed code. Node capacity 16, affinity mask 4, tiering disabled. Three shuffled fresh-process replications, seed 71933; one identical caller binary in every arm, normal fresh library builds and fixed source/executable hashes. All 288 final workers validate exact IDs; the 48 additional original-API and distant-move workers are retained in the supplementary record. The shared Global\Tedd.RTree.PerformanceHost mutex serializes cooperating builds/tests/profiles/measurements. External desktop load, thermal/frequency variation and runtime scheduling remain uncontrolled. Fresh PIDs do not prove statistical independence.

Fixture seed 73211; 10,000 or 100,000 integer-valued bounds represented exactly in int/long/float/double. Uniform or eight diagonal clusters; queries cover points, edge contacts, widths 20/200/1000 and full containment. Each operation calibrates to at least 100 ms, then measures one block. IDs are consumed; result lists are reused. Geometry/adapters are prepared outside timing; construction includes an identical small adapter. Current-thread allocation counters do not measure live memory/working set. Mutation timing measures the first 1,000 IDs displaced (+7,-9,+11) after 64 warm moves on a separate tree. It does not establish sustained churn performance.

Snapshot construction includes publication; concurrent operations include normal locking. All types preserve typed geometry and exact integer metrics. Extreme coordinates, threshold neighbors, duplicates, mixed mutation, root collapse and snapshot publication are verified separately from timing. No source change uses approximate geometry or hidden query caches.

Timing is an inspected external rig; DotNetLab provides bound CPU captures, stack analysis, hypotheses and generated-code investigation. The worker exposes no registered harness scenario; these are external normal-build measurements rather than a DotNetLab qualified confirmation result. No ReJIT/native promotion is claimed. Sampled frames include waiting threads and construction in the diagnostic loop, and do not represent per-update CPU time or call counts.

Evidence: [protocol](../Research/2026-10-18-mutation-regressions/PROTOCOL.md), [primary medians/ranges/allocation](results/mutation-regressions/final/summary.csv), [primary raw observations](results/mutation-regressions/final/samples.json), [adverse/original observations](results/mutation-regressions/adverse/summary.csv), and [prior generic packing study](../Research/2026-10-18-generic-packed/REPORT.md). The cross-language [original 2D comparison](MUTABLE-PACKED.md) uses its own retained fixture and competitor measurements.
