# Mutation regression investigation

## Scope and method

Current-control source: `79a5dd2` (NuGet 1.0.12). Historical generic STR control: `3d2d88f` (NuGet 1.0.8). Original checkout/integration branch: `main`, initially clean. The original double 2D API, generic 2D/3D and concurrent wrappers share the measured mutation changes. Snapshot trees have no individual-update operation; construction/search code is unchanged by this work.

The DotNetLab optimization skill guided diagnosis, prospective experiments, candidate disposition, code evidence and confirmation. See [protocol](PROTOCOL.md) and retained JSON/traces under this directory. Timing uses the external managed-code rig, explicitly CoreCLR 10.0.13, not a qualified native/ReJIT promotion. No diagnostic observer is present during timing.

## Candidate ledger

| Candidate | Mechanism | Disposition |
|---|---|---|
| Leaf-contained replacement, A04/A09 | Replace entry locally instead of remove/reinsert | Rejected: 3D clustered batches improved only 2–5%; one 2D post-move query aggregate regressed 18.9%. Full 54-worker exploration retained; prototype in rejected-leaf. |
| Exact metric reuse, A03 | Cache per-entry split areas, hoist group areas, reuse subtree area | Matched 54-worker exploration: update ratios 0.579–0.827; build 0.996–1.031; queries 0.986–1.013; post-move queries 0.952–1.017. All allocation guardrails and traversal fingerprints pass. Integrated source `9a61db5`; retained in final confirmation. |
| Bounded integer metrics, A09 | Exact ulong products for provably bounded extents; original BigInteger fallback | Formula oracle and all 48 integer workers pass correctness; update ratios 0.518–0.626 versus metric reuse. The exploratory query discrepancy remains retained. Integrated source 409594e. |
| Private union constructor inlining, C18 | Remove actual constructor calls/box temporaries in bulk and mutation loops | All 54 exploratory workers pass elapsed guardrails. 3D double construction ratios 0.503–0.572; all queried/mutated fingerprints agree. Integrated source cf34a58; retained in final confirmation. |
| Wider containment/grouping changes | Avoid more reinsertion by relaxing grouping | Deferred after contained replacement failed query guardrails. |
| Layout, pooling, SIMD, parallelism, blanket inlining | Additional representation/runtime changes | No measured need after eliminating repeated metric work; semantic/complexity costs do not justify speculative changes. |

The first metric-cache epoch was aborted for caller drift before its budget completed. Its partial observations remain under exploration-metrics and are excluded from conclusions for that explicit validity failure. A common caller executable plus hash assertion fixes the rig; exploration-metrics-matched completes the full budget. The integer experiment's initial admission also stopped before measurements when the metrics control had an older caller identity; distributing the common caller to every variant resolves that admission failure. No favorable-run filtering or replacement is used.

## DotNetLab baseline evidence

3D, 10k clustered, repeated construction plus 1,000 moves per cycle. Sample attribution includes build and runtime waiting threads; it is neither per-update CPU time nor a call count.

| Coordinates | Capture | Stack analysis | Selected self / inclusive observations |
|---|---|---|---|
| int | cap-5ca72d3713eb4c93bf83d05c95fb5df3 | stack-analysis-c77eab3593904ff38cb6fefd09162995 | Volume 36/38, Split 31/70, Area 19/24, ChooseSubtree 18/38, Insert 14/122; 128 waiting-thread samples of 266 total |
| double | cap-6573bc2679f6404584d946d4729d0e0c | stack-analysis-13c17d838f1f48559cc0020ede9ca172 | Split 39/67, Area 20/20, ChooseSubtree 20/20, Remove 15/19, Insert 12/99; waiting-thread samples present |

The stack evidence motivates arithmetic reuse and bounded exact specialization. It does not establish PMU/cache/branch behavior. Profile JIT output may end mid-listing when an owned target is stopped; normal-exit listings will supply the code evidence used for confirmation.

After A03/A09, a complete 432-worker matrix observes 23–59% lower update-batch times versus 1.0.12, with every matched traversal fingerprint unchanged. Some build/post-query times exceed the prospective 5% guardrail. A further 48 original/far workers retain additional flags. These are not silently classified as noise or removed.

The 135-worker stability epoch uses every flagged case, longer 1,000ms windows for its failed families and an exact duplicate control. Every long-window candidate query family is within 5%; one 3D double build remains 7.2% above the primary control. Identical-binary construction medians differ by up to 25.4%. That variability does not prove a cause for any individual flag. Tiny allocation-counter differences also occur between identical controls. The epoch changes preparation/order and cannot replace the first one. All flags remain in both CSVs.

Normal-exit baseline/candidate listings compare equal after runtime-address normalization for all 20 captured construction/query methods/thunks (generic 3D int/double, 2D long, original 2D). This supports kernel equivalence, not identical machine/cache/GC conditions. Inspecting the actual bulk listing exposes private union-constructor calls, stack temporaries and repeated box copies, motivating the separate C18 intervention instead of declaring the remaining construction guardrail passed.

Final A03/A09 CPU captures: int cap-9e5a89e78298420dba96654c3868274f / stack-analysis-7e33fe85a5f048e1b4bf7eb13b698c4d; double cap-2dbf30398b2a4cf2b619f5830ed53a64 / stack-analysis-d20caa98b3a749c795baca1c184224e8. The int capture has 296 observed samples (Volume 6 self; 146 waiting-thread); double has 294 (Split 67 self; 144 waiting-thread). Different loop rates/inlining prohibit per-update comparisons of these sample counts. Parser coverage is partial, loss status unknown, and observed symbol coverage is 1.0. Preserve these limitations rather than interpreting observations as CPU-time percentages.

## Final confirmation and decision

The frozen final source `cf34a58` includes A03/A09/C18. All 288 final workers pass geometry, ID and traversal-fingerprint checks. Across 40 mutable configurations, update-batch time is 0.423–0.699 of 1.0.12: 30–58% less time, or 1.43–2.36 times the throughput. Build ratios are 0.499–1.024 and pre-update query ratios 0.973–1.033. The default 3D double 100k uniform case builds in 5.234 ms versus 9.188 ms, and executes 1,000 warmed moves in 12.070 ms versus 23.179 ms.

Post-update query ratios span 0.879–1.056. Two 2D int uniform cases exceed the original 5% threshold by about 0.6 percentage points. The prospectively frozen 18-worker follow-up measures longer composite query windows with baseline, identical-binary alias and candidate: candidate/control ratios are 1.0460 at 10k and 1.0099 at 100k; alias/control ratios are 1.0442 and 1.0029. Query allocations are zero. All follow-up elapsed/allocation guards pass, but the changed preparation/window cannot replace the original flagged observations. A 0.3125-byte/build allocation-counter difference in concurrent 2D long remains in the primary audit; mutation/query allocations do not increase. The data support adoption of the exact, grouping-preserving changes; they do not establish universal absence of regression.

Normal-exit final listings confirm that private union-constructor calls disappear from the captured bulk loops: 3D int 1→0 calls, 3D double 3→0, 2D long 3→0. The original double API already had zero calls. All 12 captured query/caller/Collect instruction listings match the control after runtime-address normalization. See [release code evidence](release-code-evidence.json). Increased bulk instruction counts are retained, rather than equated with slower execution. Public geometry validation is unchanged.

Final DotNetLab captures are mutation-int `cap-06305342fe1d4eceb0caa3497fc2ce09` / `stack-analysis-91b294c316d24448a681d37d6091f344`, and build-double `cap-9e7ad999fd32428d8c92cca558bf2df4` / `stack-analysis-f64b2d594700430a8ef0d304bd19f89b`. Raw traces, bound process identities, hashes and parser limitations are retained under profiles-release. Notebook hypothesis revisions and retained capture/analysis records completed; optional candidate-metadata creation failed with CLI exit 1. A read-only history check found no candidate record. This optional failure does not constitute qualified confirmation or invalidate the external measurements.

Full solution Release build, correctness suite, exact integer formula oracle, local/mixed/extreme mutation checks and the existing competitor-package validators pass. Snapshot and concurrent timing is single-threaded/uncontended; race/publication correctness is tested separately.

The separate 240-process original-2D refresh gives each Rust competitor the better whole-workload median of direct Rust and optimized interop. Pinned sources/build scripts were inspected before execution; [native review](NATIVE-REVIEW.md) records provenance and transition scope. The original API's six cold mutation medians also improve, but include first-use JIT and are not the generic warmed metric. Its 100k uniform post-update query median is 1,322.19 µs versus 1,218.25 µs (+8.5%). This discrepancy remains visible in the cross-language record; unchanged query instructions and other longer-window observations do not prove its cause or erase it. Accordingly, the release claims measured mutation improvements and reports query variation, rather than claiming every observed query timing passes a regression threshold.

## Reproduction

Use a dedicated `D:\Workspaces\AI\rtree-mutation-regressions` directory. Extract historical/current source there with git archive. Inspect `benchmarks/mutation-regressions/locked.ps1`, `run.py`, `profile.py`, `summarize.py`, and `audit.py`. All build/tests/timing/capture work holds `Global\Tedd.RTree.PerformanceHost`. DotNetLab catalogs are task-local SQLite only; no external database connection is involved. Owned workers and dedicated MCP controllers stop before workspace cleanup.

Each mutation observation is one 1,000-update batch after 64 moves on another tree warm the code. It does not represent a sustained churn workload or individual latency percentile. Geometry and query IDs are checked against an independent oracle before/after moves. Result-order fingerprints include the full-cover query; metric-only changes must preserve them exactly. Allocations are current-thread managed allocations, not retained memory or working set.

Environment: Ryzen 9 5950X, Windows 11, Release x64, .NET SDK 10.0.402/runtime 10.0.13; affinity mask 4, tiering disabled. Serial fresh processes and shuffled order do not establish independent statistical sessions. Desktop activity, thermal/frequency variation and unrelated software remain uncontrolled. Medians/ranges are descriptive; no significance, tail-latency or universal-regression claim is supported.
