# Mutable packed-tree optimization

Starting branch: `main`; starting commit: `e79bd96`; working tree clean. Scope: the original mutable 2D double-coordinate `RTree<T>` used in the cross-language comparison. Generic coordinate/3D implementations retain their contracts and are regression-tested.

## Prospective protocol and semantic gates

Primary metrics: complete bulk construction and aggregate materialized intersection queries. Retain the six existing deterministic 1k/10k/100k uniform/clustered fixtures, report the four width groups independently, and include build allocation and a bulk-build-then-mutate query guardrail. Preserve inclusive boundaries, finite extreme doubles, duplicate bounds/values, append/count behavior, unsuccessful removal, all node capacities, bulk workspace reuse, and unchanged-tree concurrent searches. No lazy conversion or first-mutation rebuild is acceptable.

Exploration: three matched process blocks per variant/fixture, 100 ms calibration and measured blocks; descriptive medians/ranges. Freeze the final candidate before a separate five-block fresh-process confirmation with fresh controls. Fixed shuffled orders, CPU affinity mask 4, serial execution, identical .NET runtime/tiering settings. No favorable-run selection, exclusions, replacement samples, or budget expansion. Algorithm/layout candidates require a material benefit in the 100k workloads, no semantic failures, and no unexplained >10% aggregate regression against the preceding stage; mutation/build allocation changes must be disclosed. Small selective-query absolute costs receive separate interpretation.

Competitors: pinned `static_aabb2d_index` and `geo-index` source revisions from the preceding comparison. Release, native CPU, thin LTO, one codegen unit, preallocated output/scratch where the public API permits, no managed callbacks or marshalling. Short, allocation-free result-access and small-leaf interop calls use suppressed transitions. Long builds/searches use ordinary transitions. Also retain direct-native timings, which eliminate interop entirely and give competitors their maximum measured benefit. All result IDs must match brute force before timing. Native build/destruction and managed GC lifecycle differences remain explicit.

No database or external service is used. Downloaded indexing paths, Rust dependency build scripts, managed worker startup, and benchmark callbacks are inspected before execution. Scratch/builds/catalogs under `D:\Workspaces\AI\rtree-mutable-optimization`.

## Source findings

- `geo-index`: compute 16-bit-center Hilbert keys once, partition only to leaf-block precision, then form parents bottom-up without re-sorting each level. Primitive-key sorting avoids our index-comparer indirection.
- `static_aabb2d_index`: contiguous bounds/indices, reused traversal scratch and output visitor, root rejection, compact leaf data. Bounds and values do not carry unused child references.
- Existing Tedd bulk loading sorts indirect indices by x and y at every level, constructs intermediate `Entry[]` arrays, and allocates an unused child field in every leaf entry. Mutability is provided by the existing split/condense algorithm and does not require retaining those bulk-construction costs.

## Candidate ledger

| ID | Catalogue / registry | Mechanism | State |
|---|---|---|---|
| A1 | A01/A03; M7, R2 | Hilbert keys, primitive sorting, direct leaf construction, sequential parent packing | Tested; integrated algorithm stage, final confirmation pending |
| M5-1 | M5; M01/M02 | Separate per-node bounds, leaf values, and branch children; maintain all arrays during mutation | Pending DotNetLab profile |
| M7-1 | M7/M3 | Bulk copy fully contained leaf values into result list; preserve append semantics | Pending profile |
| M3-1 | M3/M4, R2 | Span/byref access versus surviving bounds checks and 32-byte rectangle copies | Pending generated-code evidence |
| C3-1 | C3/V01/V03/V17 | SIMD rectangle rejection with scalar fallback | Pending applicability evidence |
| M1-1 | M1/M2 | Uninitialized primitive scratch or bounded stack scratch, avoiding reads before initialization | Pending allocation/code evidence |

Catalogue coverage: M1–M7 and R2 are applicable above; C1/C2/C3/C4 require emitted-code/profile discrimination. C5 (stencils), S1–S3 (bitmaps/hash/frozen maps), S4 (query caching), S5 (compression), R1 (opcode dispatch), R3 (configuration branches), T1–T4 (coordination) are outside this single-thread mutable-tree mechanism: there are no such structures or waits in this path; query caching would introduce invalidation/memory costs rather than improve first-use traversal. Parallelism/GPU are excluded by the single-core comparison objective. Software prefetch requires unavailable PMU/locality evidence rather than a source-level assumption.

## Execution ledger

- Control source preserved before modifications. Existing benchmark source revisions pinned. DotNetLab MCP transport is closed; inspecting the documented CLI fallback and installed host/runtime before diagnostics. No client configuration changes.
- Algorithm exploration completed: 36 fresh worker processes, exact result sets before/after mutation. At 100k entries control/algorithm build medians were 31.405/14.700 ms uniform and 27.497/13.547 ms clustered. Aggregate queries were 1.487/1.416 ms uniform and 1.629/1.363 ms clustered. Post-mutation queries improved at 100k; the 1k uniform post-mutation case regressed 11.8% (24.11 to 26.96 us), flagged for final confirmation after layout work rather than concealed.
- Algorithm-stage mutation allocation fields were unmeasured placeholders; they are unavailable evidence. The final worker records actual current-thread mutation allocation.
- Existing differential/boundary suite and new mixed-mutation/extreme-double tests passed. Algorithm integrated before residual optimization. Raw exploration: `benchmarks/results/mutable-packed/algorithm/`.
- Configured DotNetLab CLI fallback is available at `dotnetlab-installations/9c23369/Tedd.DotNetLab.Host.dll`; its profiles include cpu/allocation diagnostic capture. No MCP/client reconfiguration.
- Current gate: capture algorithm query/build profiles, inspect emitted code, then test representation/copy candidates under the existing protocol.
