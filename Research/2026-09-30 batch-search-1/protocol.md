# Protocol and hypothesis ledger

Baseline revision: e37bbdca4d3781279a55af911efd40664866524c; initially clean.
Scope: local library experiments on query traversal and batch query synchronization;
bounded construction experiments explain alternative algorithms. No application workload
was supplied. Do not extrapolate these results to application-level speedups.

Primary metric: elapsed microseconds per 64 queries, consuming every returned value.
Priorities: point and small selective queries must remain within 5% of control after
independent confirmation; broad-query improvements must exceed observed dispersion.
Allocations must not increase in the reused-list path. Any API expansion must have
explicit ownership, output segmentation, and synchronization semantics.
Construction experiments preserve query correctness and include construction costs.

Fixtures: seed 73211, 10,000 finite rectangles, uniform and eight clustered placements;
point, width 20, width 200, width 1,000, entire index, and disjoint queries.
Independent oracle: direct intersection scan plus sorted complete value comparison.
Screening: 100 ms warmup, nine alternating 40 ms samples; BenchmarkDotNet ShortRun
independent confirmation. Measure list clearing consistently. No affinity pinned.
BenchmarkDotNet uses normal runtime tiering/PGO; diagnostic disassembly is separate.

## Initial hypotheses (states updated in report-data.json)

| ID | Mechanism and inspected evidence | Prediction / falsifier |
|---|---|---|
| H-001 | Search tests every descendant even when a query contains a whole node. Recursively collect contained subtrees. | Broad/all faster; reject if selective regression exceeds 5%. |
| H-002 | Root containment is sufficient for all-index queries and avoids per-node containment tests. | All faster without selective penalty; compare H-001. |
| H-003 | Only internal nodes need containment checks to skip large subtrees. | Broad faster with less selective overhead than H-001. |
| H-004 | Search loops compare node.Count and separately index node.Entries. Bound one span. | Faster selective traversal; inspect optimized range checks. |
| H-005 | Split recalculates entry areas for every seed pair. Cache areas. | Incremental construction faster with identical tie decisions. |
| H-006 | Split allocates a bool array of at most 129 entries. Use initialized bounded stack storage. | Fewer allocations without build regression. |
| H-007 | Quadratic seed selection evaluates every pair. Compare normalized-separation seeds. | Build faster; query cost must be measured independently. |
| H-008 | Concurrent searches acquire/release the reader lock for each query. Batch within one lock. | Lower selective/miss latency; retain only with defined writer exclusion. |
| H-009 | Snapshot searches read the published reference per query. Capture once per batch. | Faster batches plus one-version consistency. |
| H-010 | Incremental construction repeatedly splits; existing STR packing sorts once per level. | STR reduces initial-build cost; report query and mutation contracts. |
| H-011 | Node capacity changes tree depth and linear scan width. Compare 8/16/32/64. | Workload-dependent improvement; do not change default without balanced evidence. |
| H-012 | Existing SIMD flat scan removes traversal but examines every rectangle. | Broad competitive, selective much slower; compare after traversal optimization. |

## Evidence-derived second round

H-001/003 screening reduces broad time but regresses point queries. Source inspection
shows containment tested before the intersection pruning and at every visited leaf.
H-013 checks containment only for already intersecting internal entries (parent H-001).
H-014 combines that mechanism with H-004 bounded spans after isolated measurements.
H-015 combines internal-only containment with bounded spans (parents H-003/H-004).
H-016 routes zero-width/height queries through the original traversal; a selective
query cannot contain a nondegenerate subtree (parent H-013). This is a workload
specialization and must also validate degenerate rectangles and mutated trees.
H-017 combines the point routing and span traversal (parents H-014/H-016).
All retain the initial 5% selective-regression bound and allocation constraint.

## Third round after integration

Generic screening found a 2D-long selective regression outside 5%; retest with
independent interleaved samples before deciding. H-018 derives leaf match counts
from the appended result-list prefix instead of an integer increment per match.
H-019 bounds the collector's active array prefix with a span (parent H-014).
H-020 captures the generic node array and count in locals while retaining safe
array indexing, testing whether generic span code causes the regression (parent H-014).
These are distinct mechanisms supported by the new collector hot path and generic
regression; reject if gains are noisy or selective regression limits fail.

H-007 reduces measured construction time but produces slower medium-query trees;
it is not a general replacement. H-005/006 are initially slower or within host noise.
Independent confirmation remains required.

## Final disposition and stopping condition

H-021 tests a coordinate-specialized array path for 2D long. It restored long point
and small-query performance, but final generic acceptance remained mixed. Both
generic traversals were restored to the original implementation; their batch APIs
remain. Excluded source is preserved as experimental-2D-final.txt and
experimental-3D-final.txt and can be compiled using the investigation project's
ExperimentalGenericTraversal=true property.

H-018 showed no consistent gain over the integrated control. H-019 improved full-index
throughput further but lost 6–15% on point queries relative to that control in focused
follow-up, so the selective-query priority excludes the incremental change. H-020
corrected long queries but regressed small int/float queries when applied universally.

The retained scope is the original 2D double traversal plus batch queries on all nine
API variants. Twenty-one distinct hypotheses have recorded dispositions. All
evidence-supported mechanisms in this bounded query/batch investigation have been
tested or ruled out by the catalogue review. Different index families, automatic
scan switching, and further workload-specialized defaults require a specified
build/update/query distribution; they are algorithm alternatives, not unmeasured
library improvements. No application-level speedup is claimed.

No production/database write path exists in inspected library, fixtures, project files,
or test startup. The rig writes only local evidence/build artifacts. Package restore
uses declared package references. Scope excludes adopting a new index family without
a specified build/update/query ratio, and excludes changing visibility semantics of
existing single-query methods.

The OS-backed advisory lock is C:/Users/tedd/.codex/locks/performance-measurement.lock.
Uncoordinated applications remain a threat to validity. Record host state and every
lock acquisition in driver output. Timing is never run without the helper.
