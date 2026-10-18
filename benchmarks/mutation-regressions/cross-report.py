"""Current original-API comparison with competitors' better whole-workload medians."""
import csv
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
rows=list(csv.DictReader((root/'benchmarks/results/mutation-regressions/cross/summary.csv').open()))
def value(n,d,s,o):return float(next(r['median_us'] for r in rows if (int(r['size']),r['distribution'],r['library'],r['operation'])==(n,d,s,o)))
out=['# Mutable R-tree and independent Rust indexes','',
     f'Measured 18 October 2026. Tedd.RTree source `{sys.argv[1]}` against release-1.0.12 source `79a5dd2`, static_aabb2d_index and geo-index (Hilbert/STR). This fixture uses the original mutable 2D double API. The [generic comparison](GENERIC-PACKED.md) measures the other 2D/3D APIs separately.','',
     'Each library runs independently. Rust scores use the lower whole-workload median of direct Rust and optimized interop. No favorable individual observations are selected. Native CPU optimization, thin LTO, one codegen unit and static unsafe_optimizations give competitors their optimized release configuration.','',
     'Interop uses blittable geometry, reused native output/traversal scratch where supported, zero-copy result views and no reverse managed callbacks. SuppressGCTransition applies to trivial result access and allocation-free static leaf queries bounded to 16 entries. Larger queries/builds keep ordinary transitions; direct execution removes interop entirely. Native construction includes destruction; managed reclamation occurs during repeated builds.','',
     '## Measurements','',
     '| Entries | Distribution | Library | Build ms | Mode | 64 queries µs | Mode |',
     '|---:|---|---|---:|---|---:|---|']
labels={'candidate':'Tedd.RTree (C#)','static':'static_aabb2d_index (Rust)','geo-hilbert':'geo-index Hilbert (Rust)','geo-str':'geo-index STR (Rust)'}
for n in (1000,10000,100000):
 for d in ('uniform','clustered'):
  for name,label in labels.items():
   choices=['candidate'] if name=='candidate' else ['native-'+name,'interop-'+name]
   b=min(choices,key=lambda s:value(n,d,s,'build'));q=min(choices,key=lambda s:value(n,d,s,'queries'))
   out.append(f'| {n:,} | {d} | {label} | {value(n,d,b,"build")/1000:.3f} | {b} | {value(n,d,q,"queries"):.2f} | {q} |')
out += ['', '## Original API updates','',
        'These are the first 1,000 moves (or all entries for the 1k fixture), including first-use JIT work, unlike the generic warm64 mutation batches. Do not infer sustained throughput from these single cold batches.','',
        '| Entries | Distribution | 1.0.12 moves ms | Current moves ms | 1.0.12 post-query µs | Current post-query µs |',
        '|---:|---|---:|---:|---:|---:|']
for n in (1000,10000,100000):
 for d in ('uniform','clustered'):
  a,b,c,e=[value(n,d,s,o) for o in ('mutation','mutated') for s in ('control','candidate')]
  out.append(f'| {n:,} | {d} | {a/1000:.3f} | {b/1000:.3f} | {c:.2f} | {e:.2f} |')
out += ['', '## Method, provenance and limits','',
        '240 scheduled fresh processes completed: six deterministic fixtures, eight arms, five replications; shuffled seed81043. Source/caller/native hashes, all raw observations, launches and failure policy are retained in [the protocol](results/mutation-regressions/cross/protocol.json). Every implementation validates all 64 query result sets against brute force before timing. Node capacity16, one CPU affinity (mask4), Release x64, .NET10.0.13 with tiering disabled. Each operation calibrates to at least100ms, then measures one block. The query aggregate is the median of each process’s sum of four 16-window groups. IDs are materialized and consumed.','',
        'Geometry uses LCG seed73211; uniform coordinates or eight diagonal clusters, boxes of widths1–5, query widths0/20/200/1000. This older two-dimensional fixture differs from the dimension-specific generic fixture. Fixture parsing and prepared geometry are excluded from timing. Both before/after managed arms use an identical caller binary.','',
        'Pinned sources: [static_aabb2d_index a511a63](https://github.com/jbuckmccready/static_aabb2d_index/tree/a511a6327e14a0f0418cea01c401bf147e0e835c), [geo-index e6efbb0](https://github.com/georust/geo-index/tree/e6efbb01d3c298e8963c8b7d1aab40c1bd540715). Source/build paths and dependencies were inspected before execution; this is a limited review, not a security audit. See [native provenance](results/mutation-regressions/cross/native-provenance.json) and [review record](../Research/2026-10-18-mutation-regressions/NATIVE-REVIEW.md).','',
        'Desktop load, frequency/thermal variation and runtime scheduling are uncontrolled beyond the shared cooperating-host mutex. Fresh PIDs do not prove independence; medians/ranges are descriptive. These measurements establish neither a universal fastest library nor individual tail latency. Native allocations are unavailable, not zero; managed counters cover the current thread, not retained memory. The earlier C/C++/Go/JavaScript screening remains in [CROSS-LANGUAGE.md](CROSS-LANGUAGE.md).','',
        'Complete [medians/ranges/allocations](results/mutation-regressions/cross/summary.csv), [samples](results/mutation-regressions/cross/samples.json), [native boundaries](results/mutation-regressions/cross/native-boundaries.json), and [mutation investigation](../Research/2026-10-18-mutation-regressions/REPORT.md).','']
(root/'benchmarks/MUTABLE-PACKED.md').write_text('\n'.join(out),encoding='utf8',newline='\n')
