# Generic 2D/3D packed-tree optimization

Start: clean `main`, commit `3d2d88f`. Integration and publishing branches: `main`, `deploy`. Scratch: `D:\Workspaces\AI\rtree-generic-packed`. Preserve the pre-change library before implementation. No indexing workload accesses a database or external service. Any diagnostic catalog is local task-owned SQLite. All following builds/tests/timing/diagnostics use the shared `Global\Tedd.RTree.PerformanceHost` mutex.

## Prospective protocol

Scope: generic 2D/3D `int`, `long`, `float`, `double`, including snapshot and concurrent wrappers, which delegate to the underlying trees. Preserve exact typed geometry, inclusive intersections, duplicates, append/count behavior, all supported capacities, workspace reuse, empty/singleton/extreme cases, mutation/root collapse, and wrapper visibility contracts. Sorting keys affect grouping only. No conversion or rebuild on first mutation.

Transfer A1/M5/M7/R2 from the measured original-2D work: primitive spatial keys and radix sorting, bottom-up parent packing, typed input, separated bounds/values/children, fully contained leaf span copy. Generic predicates receive a separately evaluated inline request after algorithm adoption. Existing exact integer selection/split metrics remain unchanged. Axis normalization subtracts integer origins in Int128 before approximate key scaling; stored geometry is never converted to double.

3D candidate ordering: Skilling 10-bit-per-axis Hilbert versus 10-bit-per-axis Morton, both using all three axes and the existing four-pass uint radix sorter. Exploration: three fresh processes per variant, 3D int/double, 10k/100k, uniform/clustered; include fresh original controls. Inspect all query-width groups, build allocations, and post-move queries. Select a candidate with material construction/query benefit versus original and disclose any >10% aggregate regression; a conflicted candidate returns to investigation, never favorable sample replacement. Compare 2D transfer against fresh controls with three blocks for four types, 10k uniform. Diagnostic sampling/JIT listings are separate from timing.

Freeze source/binary identity before independent final confirmation: three fresh-process blocks, generic plain 2D/3D × four types × 10k/100k × uniform/clustered × original/candidate = 192 processes. Wrapper confirmation adds 2D/3D × four types × snapshot/concurrent × 10k uniform × three blocks × original/candidate = 96 processes. Fixed shuffle seeds, CPU affinity 4, tiering disabled, serial execution; 100 ms calibration followed by one measured block. No failed/excluded/replacement samples or post-result budget expansion. Medians and ranges are descriptive; fresh PIDs do not establish statistical independence. Build/query allocations and a separate first-use move batch are guardrails, not steady-state update throughput.

## Evidence and candidate ledger

- Retained prior DotNetLab captures establish old entry-stride, per-item collection, interface input, and predicate-call costs for the original 2D implementation. These are hypotheses for generic implementations, not forecasts of gains. Reinspect generic generated code and representative 3D profile after algorithm adoption.
- A1/R2: typed bulk input, primitive spatial keys, radix ordering, sequential parents — pending.
- M5/M7: compact mutable nodes plus contained-subtree bulk result copy — pending combined transfer; maintain all mutation paths.
- M3/R2: readonly bounds spans and predicate inline requests — pending generated-code/measurement evidence.
- M1: reuse workspace arrays for primitive keys/scatter; skip-initialization already failed prior work, so retain ordinary initialized arrays.
- C3/V: no new ISA-specific traversal without residual profile evidence; platform SIMD is already used by bulk copy where appropriate.
- C1/C2/C4: sorting work and normalization specialization applicable; no inferred cache/branch-miss claims. T/parallel/GPU/cache families outside the single-core mutable-tree objective.

Source references: [Skilling's Hilbert transform](https://doi.org/10.1063/1.1751381), [Apache Iceberg's description of the same transform](https://iceberg.apache.org/javadoc/latest/org/apache/iceberg/util/HilbertByteUtils.html), [Morton bit interleaving](https://github.com/Forceflow/libmorton). No external source is executed for these implementations.

## Ordering exploration

All 72 predeclared processes passed exact result validation. At 100k uniform double: control/Hilbert/Morton build 46.648/21.042/9.182 ms, aggregate query 1250.32/613.25/764.03 us. Clustered double: build 39.392/17.565/9.283 ms, queries 1227.74/327.35/339.39 us. Int results show the same tradeoff. Morton is retained for its greater construction benefit, reduced implementation complexity, and material query gains versus STR. Hilbert has better uniform queries; this is not concealed or called a universal Morton win. The full unselected encoding prototype is retained in ordering-prototype.cs.txt; raw binary identities, samples, and launches are under benchmarks/results/generic-packed/ordering/.

Workspace specialization also removes the obsolete double/BigInteger center arrays. All packers now share three primitive buffers (12 bytes/entry retained). Snapshot builds exercise the workspace path; ordinary builds use fresh buffers. Expanded tests cover switching types/dimensions and indexed-only input contracts.
