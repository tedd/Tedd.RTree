# Mutable packed-tree comparison

The worker measures builds, four groups of 16 materialized intersection queries, a 1,000-entry movement batch, and the same query groups after movement. Every managed process validates exact IDs before and after mutation. See the [research record](../../Research/2026-10-17-mutable-packed/REPORT.md) for prospective protocols, source identities, decisions, and final results.

Use a dedicated workspace under `D:\Workspaces\AI\`. Preserve the original `src/Tedd.RTree` sources and build them to `control/Tedd.RTree.dll` before changing production code. Competitor source revisions are pinned by the prior [source lock](../cross-language/sources.lock.json); check out `geo-index` and `static-aabb` beside `native/` in the workspace.

`locked.ps1` serializes builds/tests/measurements using `Global\Tedd.RTree.PerformanceHost`. `build-control` builds the identical worker against the preserved library, while `build-algorithm` and `build-candidate` build against the current source. `algorithm`, `layout`, and `confirmation` execute fixed prospective comparison budgets. Example:

```powershell
.\benchmarks\mutable-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-mutable-optimization -Action build-candidate
.\benchmarks\mutable-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-mutable-optimization -Action test
.\benchmarks\mutable-packed\locked.ps1 -Workspace D:\Workspaces\AI\rtree-mutable-optimization -Action confirmation
```

For native comparisons, `native.ps1 -Action fetch` stages manifests and fetches dependency source without compiling it; inspect dependency build scripts first. `-Action build` produces a release Rust DLL and executable with native CPU code generation, thin LTO, and one codegen unit. The static Rust competitor uses its `unsafe_optimizations` feature, preallocated output, and reused traversal scratch. Geo-index uses its public search implementation and both packing algorithms.

The C ABI uses blittable rectangles, opaque owned handles, and a zero-copy pointer/count view over native results. There are no reverse callbacks. Only trivial result access and static leaf queries with at most 16 entries use `SuppressGCTransition`; builds, destruction, and larger queries retain ordinary transitions. The result view remains valid only until the next query or destruction. Direct-native measurements eliminate interop entirely; both direct and interop results are preserved, and competitor comparisons use the lower median per workload to give native implementations maximum benefit. Native allocation is not captured by .NET allocation counters and must not be interpreted as zero allocation.

Queries return IDs into reusable storage and consume every ID. Construction prepares geometry outside timing and includes each language's normal index lifetime costs. Managed allocation values come from current-thread allocation counters. Process/block averages are descriptive throughput measurements, not individual tail latency. CPU affinity is mask 4; background applications and power policy remain uncontrolled. .NET tiering is disabled in the comparison for matching fully optimized JIT compilation across all source arms; it is recorded separately from diagnostic collection.
