# Specialization and dispatch

The research does not establish one implementation that dominates every retained operation. Treat that as a measured tradeoff, rather than assuming an instruction or interface can remove it.

The proposed `PackedRTree<T>` is an immutable 2D index with double coordinates. Construction computes a Hilbert key for each rectangle center, orders entries by key, groups consecutive entries into leaves and builds bounding boxes upward. Bounds are stored in a flat array, payloads in one owned contiguous array, and child ranges follow from level offsets and node capacity. Stored geometry remains exact; quantization affects ordering only.

Search rejects nonintersecting bounding boxes. If a query contains a whole subtree, its payloads occupy one contiguous range, so the implementation appends that span directly. Otherwise it descends and tests leaf rectangles. This removes node allocations, child-reference arrays, mutation slack and repeated contained-leaf collector visits. It changes representation and the amount of work performed.

Eight Hilbert transforms run together through `Vector256<uint>` when hardware acceleration is available. Coordinate normalization, scalar tails and fallback remain exact relative to the scalar key implementation. The accepted direction uses scalar tree traversal. The tested scalar/128/256 column layouts and the direct-leaf SIMD remedy failed their complete-caller gates. Wider vectors did not establish a query gain.

This remains managed C#. It uses arrays, bounded stack scratch, spans and the standard span-based `AddRange` API. It neither edits private `List<T>` fields nor suppresses GC transitions in the managed index. Standard .NET bulk operations can themselves use optimized native instructions. Availability of intrinsics does not establish their profitability: [Microsoft's SIMD guidance](https://learn.microsoft.com/en-us/dotnet/standard/simd) and [Vector256 hardware-acceleration contract](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.intrinsics.vector256.ishardwareaccelerated) describe capability, not a target speedup. Retained JIT listings and complete-caller measurements supply the target evidence.

## Public contracts in the reviewable proposal

- `IReadOnlySpatialIndex<TBounds,T>`: `Count`, both `Search` overloads and `SearchBatch`.
- `IMutableSpatialIndex<TBounds,T>` derives from it and adds `Insert`, `Remove`, `Update` and `Clear`.
- `PackedRTree<T>` implements only reads. Its constructor copies input; caller arrays and optional exclusive workspace may be reused after construction. Concurrent reads need separate result lists.
- The existing three plain trees implement the mutable contract. The six snapshot/concurrent types implement the common read contract; their existing update/visibility APIs retain their distinct semantics.

An interface permits replacement at a read-only call site; it does not make an immutable tree usable at a call site that requires mutation. A read-only interface also does not make a mutable implementation immutable or synchronize it. Generic-coordinate and 3D packed implementations are not included in this proposal.

## What can be selected automatically

| Information | Available when | Valid use |
|---|---|---|
| Entry count, coordinate type, capacity, supported ISA | Construction | Size-dependent sorting, numeric specialization, guarded vector code |
| Entry distribution and tree bounds | Construction | Packing and representation choices, charged to build cost |
| Current query bounds and subtree containment | Each query | Exact pruning and contiguous-subtree copying |
| Future build/read ratio, mutation frequency, latency priorities | Generally unavailable | Explicit caller intent or separately measured adaptation |

Future workload cannot be inferred reliably from one query or the constructor. A factory can accept explicit immutability/optimization intent, but no automatic backend-selection policy is validated here. Building two backends, maintaining telemetry, converting after observed queries or caching results would add costs that must be measured. Do not select by benchmark fixture name or report the best experimental backend per cell as one implementation.

For a build-once workload, immutable packed storage is a defensible separate class. For individual moves/removals or immediately visible writes, retain the existing mutable/concurrent choices. Read-heavy snapshot publication is another possible immutable-backend application, but this proposal only shares the read interface; it does not replace snapshot internals.

## Remaining hypotheses

| Technique | Disposition and required evidence |
|---|---|
| Generic struct visitor or caller-owned span output | Untested on this packed backend. Could remove intermediate materialization; benchmark exact visitation separately from a materialized-results contract. It cannot silently replace the latter with count-only work. |
| Lossless narrower storage or quantized secondary bounds | Untested. Arbitrary doubles cannot be narrowed to float losslessly. Conservative screening must retain exact bounds and charge extra storage/build/verification. |
| Different partial-selection algorithm | The tested stable MSD implementation and call-guard remedy failed; that does not rule out quickselect or another algorithm. Needs a distinct source hypothesis and frozen budget. |
| Chunked bounds, pooled storage, unmanaged allocation | Not adopted. Existing scratch reuse is explicit. Diagnose the construction-size discontinuity before attributing it to GC or proposing disposal/lifetime complexity. |
| CPU prefetch, AVX-512, PGO/AOT or multi-core policies | No general gain established. This host lacks AVX-512; prefetch needs locality evidence, AOT needs its own runtime comparison, and parallel work changes the one-core objective. Ordinary tiering is separately checked. |
| Aggressive inlining, BMI2 PDEP, fused histograms, whole-index vector scans | Earlier retained studies rejected these specific changes under their declared gates. They are not untested shortcuts. |
| NoInlining on the recursive query helper | Tested after actual Tier1 code expansion. Shrinks the body but gains only 7.8% on the targeted workload, below the frozen 10% gate; not adopted. |

No conclusion covers every CPU, data distribution, query schedule or mutation regime. Correctness checks, favorable medians and a finite comparison matrix do not establish universal dominance or exhaustive optimization.
