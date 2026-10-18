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

## Algorithm adoption and residual diagnostics

Algorithm stage integrated as dec33fc before residual optimization. All expanded tests passed. At 10k uniform, generic 2D builds improved from 3.637 to 0.645 ms (double), 2.053 to 0.600 ms (float), 2.781 to 0.583 ms (int), 5.516 to 0.674 ms (long); aggregate queries improved from 211–235 us to 102–105 us. All 24 transfer processes passed.

DotNetLab query capture cap-9fd8aa99065c49ef8e9b6723e480b4df, analysis stack-analysis-ee9cacc94e2d4d72b5c055cf90b44386; build capture cap-9f2e8dcb891943779ceda2509007b599, analysis stack-analysis-cf1b4d046c1a4bf48788b2f7b8dbb5cd. Dedicated task-owned catalog verified at D:\Workspaces\AI\rtree-generic-packed\lab. Query self counts: traversal 48, caller/consumption 14, collection 6, memmove 2. Build: packed constructor 111, radix 18. Wait-thread samples are also present; none of these counts establishes CPU fractions or per-call costs. Traces are retained with SHA-verified artifact provenance. Diagnostic JIT tails can be partial because workers terminate after capture; complete normal-exit listings are retained separately.

Optimized generic int/double JIT listings retain geometry predicate calls in traversal. Prospective inline experiment: add requests only to generic Rectangle2D/Box Intersects and Contains. Three matched blocks for 3D int/double at 100k uniform/clustered plus 2D all four types at 10k uniform, 48 processes, seed 92731. Require material large-query benefit with no unexplained >10% aggregate regression; preserve mutation/allocation guardrails and all typed semantics. Do not assume an attribute proves inlining; inspect the emitted code.

## Inline disposition and final freeze

All 48 inline processes passed. Generic 2D 10k uniform aggregate queries improved from 102–105 us to 78–84 us across the four types. 3D 100k uniform: int 696.95 to 575.89 us, double 758.49 to 681.66 us; clustered also improved modestly. Full normal-exit JIT listings contain no predicate calls in retained traversal. Retain inline requests without claiming they guarantee inlining on every runtime. No primary aggregate query regression occurred.

Final production source is frozen after metadata/docs updates and the expanded snapshot-publication test. Run the original 288-process confirmation budget with fresh control/candidate callers and matching runtime. Every production source hash and executable identity is retained in the protocol. Final diagnostics are separate from timing; no extra favorable measurements or omitted failures.

Final diagnostic reprofile of the frozen source: query cap-f11f63f3c65d4ae699304bd8be156e92 / stack-analysis-ea0582c6da8d4e278cfef9b2d49b17fe; build cap-cd0c03e91b954cfaae91caf1e4cc4268 / stack-analysis-95246056c2b841a4be86032f70cce006. Query self counts: traversal 48, caller/consumption 16, memmove 7, collection 3. Build: packed constructor 128, radix 12. Sample totals and waiting frames vary; no causal speed ratio is inferred from these counts. Candidate normal-exit int/double JIT listings verify predicate call removal and retained generic specializations. All capture/analysis operations completed, and owned targets/controllers exited before confirmation.

Catalogue disposition: A1/R2 and combined M5/M7 supported by isolated ordering/transfer experiments; M3/R2 predicate inline requests supported by generated code plus 48-process comparison. M1 retains initialized buffers and the shared 12-byte/entry workspace; prior skipped-initialization evidence did not justify another speculative variant. C3/V intrinsics, software prefetch, parallelism, GPU, and query caching are deferred for lack of a measured bottleneck/fit within this portable single-core mutable API objective. This is not a claim of exhaustive optimization.

Production .cs/.csproj source is frozen at 04028ea; the confirmation protocol stores every file hash. Subsequent website/report/README edits describe the implementation and do not alter the measured production code. The README precision statement distinguishes exact stored bounds and selection metrics from approximate grouping keys.

## Final confirmation and adoption

All 288 scheduled fresh processes completed without failure or exclusion. Every primary build and aggregate-query median improved, including all snapshot/concurrent cases. At 100k, generic 2D builds improved 3.44–4.98x and queries 2.70–3.25x; 3D builds improved 4.73–5.56x and queries 1.80–3.80x. Representative 3D double uniform: build 43.196 to 9.087 ms; 64 queries 1255.57 to 695.62 us. Every post-move aggregate query median improved.

Mutation guardrails are mixed: 10k clustered plain batches regressed up to 52.1%; 100k uniform 3D batches regressed up to 13.6%; clustered 100k batches improved. The complete CSV retains all sizes/models, and the public report now lists both sizes for plain movement, rather than showing only the more favorable 100k clustered cases. Batch timings are once per process after 64 warm moves; unvisited paths may still incur first-use work. Grouping changes can affect split/condensation work, but this rig does not isolate the cause. Adoption explicitly prioritizes the substantial bulk/query improvements and preserves direct mutability; no universal update-throughput gain is claimed. This tradeoff is visible on the webpage and in the report.

Post-confirmation hash verification matched every frozen production .cs/.csproj file. Full Release solution build, expanded tests, competitor validation, and NuGet pack passed (existing compatibility warnings for old comparison packages remain). The packed assembly is C# Tedd.RTree.dll only; no Rust native runtime is packaged. Browser verification passed all 48 chart selections with no console errors. No production code changes followed confirmation.
