"""Publish the complete matched before/after evidence without selecting favorable observations."""
import csv
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
candidate=sys.argv[1]
folder=root/'benchmarks/results/mutation-regressions/final'
rows=list(csv.DictReader((folder/'summary.csv').open()))
protocol=json.loads((folder/'protocol.json').read_text())
processes=json.loads((folder/'processes.json').read_text())
assert len(processes)==len(protocol['jobs'])==288
fields=('dimension','coordinate','size','distribution','mode')
keys=sorted({tuple(r[k] for k in fields) for r in rows})
def value(key,stage,operation):
    return float(next(r['median_us'] for r in rows if tuple(r[k] for k in fields)==key and r['stage']==stage and r['operation']==operation))
mutation_keys=[k for k in keys if k[-1]!='snapshot']
ratios=[value(k,'candidate','mutation')/value(k,'baseline','mutation') for k in mutation_keys]
historical=[]
out=['# Generic 2D and 3D performance','',
     f'Measured 18 October 2026: current source `{candidate}` against packed source `79a5dd2` (NuGet 1.0.12) in fresh matched processes. The implementation uses Hilbert ordering in 2D, three-axis Morton ordering in 3D, radix sorting and compact mutable nodes. Split/subtree metrics are reused; bounded integer products are exact, with BigInteger fallback for large extents. Individual updates retain remove/reinsert semantics and identical traversal fingerprints.','',
     f'The 40 mutable configurations have current/1.0.12 update-time ratios of {min(ratios):.3f}–{max(ratios):.3f}. Private bounds-union constructors are selectively inlined after generated-code inspection. These are complete 1,000-move batches, not individual latency percentiles. Construction, pre-update queries, post-update queries, allocation and every process range remain visible in the complete CSV and guardrail audit.','',
     '## Construction and queries','',
     '| API | Coordinates | Entries | Distribution | 1.0.12 build ms | Current build ms | 1.0.12 queries µs | Current queries µs |',
     '|---|---|---:|---|---:|---:|---:|---:|']
for k in keys:
    dim,t,n,d,m=k
    values=[value(k,s,o) for o in ('build','queries') for s in ('baseline','candidate')]
    out.append(f'| {dim}D {m} | {t} | {int(n):,} | {d} | {values[0]/1000:.3f} | {values[1]/1000:.3f} | {values[2]:.2f} | {values[3]:.2f} |')
out += ['', '## Mutable update batches','',
        '| API | Coordinates | Entries | Distribution | 1.0.12 ms | Current ms | Current/1.0.12 | Post-update queries µs |',
        '|---|---|---:|---|---:|---:|---:|---:|']
for k in mutation_keys:
    dim,t,n,d,m=k
    previous,current=[value(k,s,'mutation') for s in ('baseline','candidate')]
    out.append(f'| {dim}D {m} | {t} | {int(n):,} | {d} | {previous/1000:.3f} | {current/1000:.3f} | {current/previous:.3f} | {value(k,"candidate","mutated"):.2f} |')
out += ['', '## Guardrails and interpretation','',
        'The [guardrail audit](results/mutation-regressions/final/guardrails.csv) reports every current/1.0.12 median ratio and allocation counter, including failures of the prospective 5% elapsed threshold or exact allocation threshold. Read the [investigation report](../Research/2026-10-18-mutation-regressions/REPORT.md) for candidate disposition, contradictory observations, generated-code evidence and the acceptance decision. No flag is silently removed as noise.','',
        'All final construction and pre-update query medians remain within the 5% threshold. Two 2D int post-update query medians are 5.6% higher. A prospectively frozen [18-worker longer-window check](results/mutation-regressions/final-query-guard/summary.csv) gives candidate/control ratios of 1.046 and 1.010, with zero query allocation; its different preparation and composite windows cannot replace the original observations. A 0.3125-byte/build concurrent allocation-counter flag is also retained. Mutation and query allocations do not increase.','',
        'Earlier source epochs and every failed/inconclusive guardrail remain in the investigation record. The rejected leaf-contained replacement prototype changed later tree shape and regressed one post-update query aggregate by 18.9%. It is excluded. The integer exploration also observed one 12.4% post-query median discrepancy and a 4.5-byte/build allocation discrepancy; these remain retained separately from fresh confirmation.','',
        '## Method and limits','',
        'Ryzen 9 5950X, Windows 11, .NET SDK 10.0.402/runtime 10.0.13, Release x64 managed code. Node capacity 16, affinity mask 4, tiering disabled. Three shuffled fresh-process replications, seed 71933; one identical caller binary in every arm, normal fresh library builds and fixed source/executable hashes. All 288 final workers validate exact IDs; the 48 additional original-API and distant-move workers are retained in the supplementary record. The shared Global\\Tedd.RTree.PerformanceHost mutex serializes cooperating builds/tests/profiles/measurements. External desktop load, thermal/frequency variation and runtime scheduling remain uncontrolled. Fresh PIDs do not prove statistical independence.','',
        'Fixture seed 73211; 10,000 or 100,000 integer-valued bounds represented exactly in int/long/float/double. Uniform or eight diagonal clusters; queries cover points, edge contacts, widths 20/200/1000 and full containment. Each operation calibrates to at least 100 ms, then measures one block. IDs are consumed; result lists are reused. Geometry/adapters are prepared outside timing; construction includes an identical small adapter. Current-thread allocation counters do not measure live memory/working set. Mutation timing measures the first 1,000 IDs displaced (+7,-9,+11) after 64 warm moves on a separate tree. It does not establish sustained churn performance.','',
        'Snapshot construction includes publication; concurrent operations include normal locking. All types preserve typed geometry and exact integer metrics. Extreme coordinates, threshold neighbors, duplicates, mixed mutation, root collapse and snapshot publication are verified separately from timing. No source change uses approximate geometry or hidden query caches.','',
        'Timing is an inspected external rig; DotNetLab provides bound CPU captures, stack analysis, hypotheses and generated-code investigation. The worker exposes no registered harness scenario; these are external normal-build measurements rather than a DotNetLab qualified confirmation result. No ReJIT/native promotion is claimed. Sampled frames include waiting threads and construction in the diagnostic loop, and do not represent per-update CPU time or call counts.','',
        'Evidence: [protocol](../Research/2026-10-18-mutation-regressions/PROTOCOL.md), [primary medians/ranges/allocation](results/mutation-regressions/final/summary.csv), [primary raw observations](results/mutation-regressions/final/samples.json), [adverse/original observations](results/mutation-regressions/adverse/summary.csv), and [prior generic packing study](../Research/2026-10-18-generic-packed/REPORT.md). The cross-language [original 2D comparison](MUTABLE-PACKED.md) uses its own retained fixture and competitor measurements.','']
(root/'benchmarks/GENERIC-PACKED.md').write_text('\n'.join(out),encoding='utf8',newline='\n')
print('Updated generic comparison; update ratios current/1.0.12',min(ratios),max(ratios))
