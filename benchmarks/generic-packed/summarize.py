"""Retain every block and report dimension/type/API-specific medians and ranges."""
import csv
import json
from pathlib import Path
import statistics
import sys

base = Path(__file__).resolve().parents[1]
phase = sys.argv[1] if len(sys.argv) > 1 else 'confirmation'
folder = base / 'results/generic-packed' / phase
data = json.loads((folder/'samples.json').read_text())
processes = json.loads((folder/'processes.json').read_text())
protocol = json.loads((folder/'protocol.json').read_text())
assert len(processes) == len(protocol['jobs'])
fields = ('dimension','coordinate','size','distribution','mode','stage')
identities = sorted({tuple(d[k] for k in fields) for d in data})
rows = []
for key in identities:
    subset = [d for d in data if tuple(d[k] for k in fields) == key]
    operations = {d['operation'] for d in subset} | {'queries'}
    if any(d['operation'].startswith('mutated') for d in subset): operations.add('mutated')
    for operation in sorted(operations):
        if operation in ('queries','mutated'):
            prefix = 'query' if operation == 'queries' else 'mutated'
            values = [sum(d['microseconds'] for d in subset if d['block']==block and d['operation'].startswith(prefix)) for block in range(3)]
            allocations = [sum(d['allocation_bytes'] for d in subset if d['block']==block and d['operation'].startswith(prefix)) for block in range(3)]
        else:
            observations = [d for d in subset if d['operation']==operation]
            assert len(observations)==3
            values, allocations = [d['microseconds'] for d in observations], [d['allocation_bytes'] for d in observations]
        rows.append(dict(zip(fields,key),operation=operation,median_us=statistics.median(values),min_us=min(values),max_us=max(values),
                         allocation_bytes=statistics.median(allocations)))
with (folder/'summary.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
if phase != 'confirmation': sys.exit(0)

def row(dim,coordinate,size,distribution,mode,stage,operation):
    return next(r for r in rows if tuple(r[k] for k in fields)==(dim,coordinate,size,distribution,mode,stage) and r['operation']==operation)

report = ['# Generic 2D and 3D packed-tree comparison','',
          'Measured 18 October 2026: candidate production source `04028ea` against unchanged source `3d2d88f` (library behavior from NuGet 1.0.8). The current implementation uses Hilbert keys in 2D and three-axis Morton keys in 3D, primitive radix sorting, bottom-up packing, compact mutable nodes, and bulk copying of contained leaves. Plain, snapshot, and concurrent APIs share these implementations. Typed bounds and exact integer selection/split metrics remain intact.','',
          'All measured build and aggregate-query medians improved. At 100,000 entries, 3D construction improved 4.73–5.56× and aggregate queries 1.80–3.80× across the four types and two distributions. Mutability remains direct, with a performance tradeoff: some 10,000-entry clustered move batches were up to 52.1% slower, and 100k uniform 3D moves up to 13.6% slower. All post-move aggregate queries improved. The adoption prioritizes bulk construction and search; it does not claim universally faster updates.','',
          '## Plain mutable APIs','',
          'Median of three fresh-process block averages; lower is faster. Query figures are the median of the within-process sums of four separately measured groups of 16 windows. All returned IDs are materialized and consumed. Each row compares identical coordinate/dimension/fixture/API regimes.','',
          '| API | Coordinates | Entries | Distribution | Old build ms | New build ms | Build speedup | Old 64 queries µs | New 64 queries µs | Query speedup |',
          '|---|---|---:|---|---:|---:|---:|---:|---:|---:|']
for dim in (2,3):
    for coordinate in ('int','long','float','double'):
        for size in (10000,100000):
            for distribution in ('uniform','clustered'):
                a,b=[row(dim,coordinate,size,distribution,'plain',stage,'build')['median_us'] for stage in ('control','candidate')]
                c,d=[row(dim,coordinate,size,distribution,'plain',stage,'queries')['median_us'] for stage in ('control','candidate')]
                report.append(f'| {dim}D | {coordinate} | {size:,} | {distribution} | {a/1000:.3f} | {b/1000:.3f} | {a/b:.2f}× | {c:.2f} | {d:.2f} | {c/d:.2f}× |')
report += ['', '## Snapshot and concurrent APIs','',
           '10,000 uniform entries. Snapshot construction includes `ReplaceAll`; concurrent construction includes `BulkLoad` and disposal. These wrapper measurements include their normal publication/locking work. Snapshots replace complete batches rather than moving individual entries.','',
           '| API | Coordinates | Update model | Old build ms | New build ms | Old 64 queries µs | New 64 queries µs |',
           '|---|---|---|---:|---:|---:|---:|']
for dim in (2,3):
    for coordinate in ('int','long','float','double'):
        for mode in ('snapshot','concurrent'):
            values=[row(dim,coordinate,10000,'uniform',mode,stage,operation)['median_us'] for operation in ('build','queries') for stage in ('control','candidate')]
            report.append(f'| {dim}D | {coordinate} | {mode} | {values[0]/1000:.3f} | {values[1]/1000:.3f} | {values[2]:.2f} | {values[3]:.2f} |')
report += ['', '## Mutation guardrails','',
           'Plain trees: move the first 1,000 entries through the public API, with 64 moves on a separate tree warming the code beforehand. Mutation batches are timed once per process, so their ranges and inference differ from calibrated query/build throughput; unvisited paths can still incur first-use work. Exact result sets are checked again afterward. Tree grouping changes split/condensation work; this harness does not isolate the cause of the observed regressions. Concurrent move-batch data is also retained in the complete CSV.','',
           '| API | Coordinates | Entries | Distribution | Old moves ms | New moves ms | Old post-move queries µs | New post-move queries µs |',
           '|---|---|---:|---|---:|---:|---:|---:|']
for dim in (2,3):
    for coordinate in ('int','long','float','double'):
        for size in (10000,100000):
            for distribution in ('uniform','clustered'):
                values=[row(dim,coordinate,size,distribution,'plain',stage,operation)['median_us'] for operation in ('mutation','mutated') for stage in ('control','candidate')]
                report.append(f'| {dim}D | {coordinate} | {size:,} | {distribution} | {values[0]/1000:.3f} | {values[1]/1000:.3f} | {values[2]:.2f} | {values[3]:.2f} |')
report += ['', '## Method, evidence and limits','',
           'Ryzen 9 5950X, Windows 11 build 26200, .NET SDK 10.0.402/runtime 10.0.13, Release x64 managed code. CPU affinity mask 4, tiering disabled, serial workers under `Global\\Tedd.RTree.PerformanceHost`. Three matched fresh-process blocks; fixed shuffled order and seed 47381; 100 ms calibration followed by one measured block. All 288 scheduled processes validate exact IDs before timing; mutable APIs additionally validate after movement. No observer is active during timing. Background desktop activity is uncontrolled; fresh PIDs are not proof of independent samples. No tail-latency or significance claims.','',
           'The new fixture is explicitly 2D or 3D, with seed 73211, integer-valued coordinates represented exactly in all four types, and widths 0/20/200/1000. It includes nonempty points, edge contacts, and full containment. Geometry/adapters are prepared outside timing; index construction includes a small identical harness adapter in both arms. Build allocations measure the current managed thread, not live memory or process working set. Query timings include result consumption and interface adapter dispatch.','',
           'Correctness includes mixed insert/remove/update, duplicate bounds/reference values, capacities 4/5/16/128, root collapse, empty/singleton/radix-size cases, signed/extreme coordinates, isolated subnormal extents, adjacent long values beyond 2^53, a z-only long dataset, indexed-only sources, source-order preservation, append/count semantics, cross-type/dimension workspace reuse, and wrapper batch/concurrency contracts. Search comparisons never use quantized keys. Reusable workspace primitive buffers require 12 bytes per reserved entry, excluding array/object headers.','',
           'The 3D exploration compared both Hilbert and Morton ordering with unchanged controls. Morton was retained for substantially faster construction; Hilbert had faster uniform queries. This choice does not establish a universal best ordering. Rust competitors from the earlier comparison implement 2D indexing; their timings are not reused as 3D competitors. The original unsuffixed 2D implementation retains its separate historical comparison.','',
           'DotNetLab diagnostic captures and optimized JIT listings are separate from confirmation workers. These changed-dependency external targets use the ordinary diagnostic lane; no qualified native promotion is claimed. The ledger preserves candidate decisions, contradictory observations, and diagnostic IDs in the [research record](../Research/2026-10-18-generic-packed/REPORT.md).','',
           'Raw [samples](results/generic-packed/confirmation/samples.json), [launch records](results/generic-packed/confirmation/processes.json), [frozen protocol and binary hashes](results/generic-packed/confirmation/protocol.json), and [complete medians, ranges and allocations](results/generic-packed/confirmation/summary.csv) are retained. Exploration results are in adjacent `ordering`, `transfer`, and `inline` directories. Reproduce with `generic-packed/locked.ps1` after staging the original control library in a designated workspace, then `generic-packed/summarize.py`.', '']
(base/'GENERIC-PACKED.md').write_text('\n'.join(report),encoding='utf8',newline='\n')
