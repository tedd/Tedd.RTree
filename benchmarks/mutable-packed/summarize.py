"""Summarize the predeclared confirmation; retain all process blocks and ranges."""
import csv
import json
from pathlib import Path
import statistics

base = Path(__file__).resolve().parents[1]
folder = base / 'results/mutable-packed/confirmation'
data = json.loads((folder / 'samples.json').read_text())
processes = json.loads((folder / 'processes.json').read_text())
assert len(processes) == 240 and all(p['returncode'] == 0 for p in processes)
rows = []
for n in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        for library in sorted({d['library'] for d in data}):
            subset = [d for d in data if (d['size'], d['distribution'], d['library']) == (n, distribution, library)]
            for operation in sorted({d['operation'] for d in subset} | {'queries'} | ({'mutated'} if library in ('control', 'candidate') else set())):
                if operation in ('queries', 'mutated'):
                    prefix = 'query' if operation == 'queries' else 'mutated'
                    values = [sum(d['microseconds'] for d in subset if d['round'] == r and d['operation'].startswith(prefix)) for r in range(5)]
                    allocation = [sum(d['allocation_bytes'] for d in subset if d['round'] == r and d['operation'].startswith(prefix)) for r in range(5)] if library in ('control', 'candidate') else []
                else:
                    selected = [d for d in subset if d['operation'] == operation]
                    assert len(selected) == 5
                    values = [d['microseconds'] for d in selected]
                    allocation = [d['allocation_bytes'] for d in selected if d['allocation_bytes'] is not None]
                rows.append(dict(size=n, distribution=distribution, library=library, operation=operation,
                                 median_us=statistics.median(values), min_us=min(values), max_us=max(values),
                                 median_allocation_bytes=statistics.median(allocation) if allocation else None))
with (folder / 'summary.csv').open('w', newline='') as output:
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)

def value(n, distribution, library, operation, field='median_us'):
    return next(r[field] for r in rows if (r['size'], r['distribution'], r['library'], r['operation']) == (n, distribution, library, operation))

text = ['# Mutable packed-tree comparison', '',
        'Measured 2026-10-17. Candidate source: `a5d902c`; unchanged control library from `e79bd96` (same production code as the preceding cross-language comparison). Scope: original mutable `RTree<T>` with 2D double coordinates. Generic 2D/3D trees remain regression-tested.', '',
        'Hilbert ordering, radix sorting, and bottom-up packing reduce construction work. Separate bounds/value/child arrays enable bulk copying fully contained leaves. Existing insertion, splitting, removal, condensation, and update paths remain active; mutation triggers no conversion or rebuild.', '',
        'At 100,000 entries, construction improved 4.18–4.40× and aggregate queries improved 1.72–2.01× against the unchanged control. Tedd’s aggregate query median was lower than both Rust indexes in five of six fixtures; static_aabb2d_index remained faster for 1,000 uniform entries and usually for the most selective queries. The 10,000-uniform aggregate margin is only about 1%, which should not be treated as a robust ranking. At 100,000 entries, Tedd took 0.865/0.810 ms for aggregate queries versus static’s 1.222/1.276 ms (uniform/clustered).', '',
        '## Fresh-process confirmation', '',
        'Each cell is the median of five fresh-process block averages. Queries materialize all IDs and consume them; the aggregate is the median of each process’s sum of four 16-query groups. Lower is faster. Ranges and allocations are in [summary.csv](results/mutable-packed/confirmation/summary.csv); all samples, launch records, and prospective shuffled schedules are retained alongside it.', '',
        '| Entries | Distribution | Old build ms | New build ms | Build speedup | Old 64 queries µs | New 64 queries µs | Query speedup |',
        '|---:|---|---:|---:|---:|---:|---:|---:|']
for n in (1000,10000,100000):
    for dist in ('uniform','clustered'):
        oldb,newb = [value(n,dist,x,'build') for x in ('control','candidate')]
        oldq,newq = [value(n,dist,x,'queries') for x in ('control','candidate')]
        text.append(f'| {n:,} | {dist} | {oldb/1000:.3f} | {newb/1000:.3f} | {oldb/newb:.2f}× | {oldq:.2f} | {newq:.2f} | {oldq/newq:.2f}× |')
text += ['', '## Competitors', '',
         'Pinned revisions: [`static_aabb2d_index`](https://github.com/jbuckmccready/static_aabb2d_index/tree/a511a6327e14a0f0418cea01c401bf147e0e835c), [`geo-index`](https://github.com/georust/geo-index/tree/e6efbb01d3c298e8963c8b7d1aab40c1bd540715). Rust release uses native CPU instructions, thin LTO, one codegen unit, and static index `unsafe_optimizations`. Source indexing paths and dependency build scripts were inspected before execution; this was a limited review, not a security audit.', '',
         'Each competitor has direct Rust and C ABI measurements. Direct construction measures the index alone, excluding bridge output/scratch setup. Interop uses blittable geometry, zero-copy result views, no reverse managed callbacks, and reused traversal scratch/output where supported. `[SuppressGCTransition]` is used on trivial result access and allocation-free static leaf queries bounded to 16 entries. Builds and larger searches retain ordinary transitions, as required by the [runtime contract](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.suppressgctransitionattribute). Direct Rust eliminates interop entirely. The tables give each competitor the lower **whole-workload median** of direct and interop execution; individual favorable samples are never selected.', '',
         'The Rust indexes are immutable. Tedd retains mutability. Native destruction is included in construction; managed construction leaves reclamation to GC during repeated builds. Allocation figures cover managed current-thread allocations only; unavailable native allocation is recorded as unavailable.', '']
for n in (1000,10000,100000):
    for dist in ('uniform','clustered'):
        text += ['', f'### {n:,} entries, {dist}', '',
                 '| Library | Best build ms (mode) | Point µs | Width 20 µs | Width 200 µs | Width 1,000 µs | Best aggregate µs (mode) |',
                 '|---|---:|---:|---:|---:|---:|---:|']
        for name in ('candidate','static','geo-hilbert','geo-str'):
            choices = ['candidate'] if name == 'candidate' else ['native-'+name,'interop-'+name]
            b = min(choices,key=lambda x:value(n,dist,x,'build'))
            q = min(choices,key=lambda x:value(n,dist,x,'queries'))
            groups = ' | '.join(f'{value(n,dist,q,"query"+str(i)):.2f}' for i in range(4))
            text.append(f'| {"Tedd mutable" if name == "candidate" else name} | {value(n,dist,b,"build")/1000:.3f} ({b}) | {groups} | {value(n,dist,q,"queries"):.2f} ({q}) |')
text += ['', '## Mutation and allocation guardrails', '',
         'After bulk loading, each managed process moves the first min(N, 1,000) entries using public `Update`, validates every result against brute force, then measures the same query groups. Move batches are timed once per process and include first-use JIT work; they have less repetition and greater startup sensitivity than the primary metrics. These measured batches regressed by up to 14.2% in the smaller fixtures and 9.3% at 100k uniform; 100k clustered was slightly faster. Adoption accepts this disclosed guardrail tradeoff for the primary build/query improvements. These data do not establish steady-state update throughput. Post-move aggregate queries improved in all six fixtures; build allocations fell by approximately 53% at 100k.', '',
         '| Entries | Distribution | Old moves ms | New moves ms | Old post-move queries µs | New post-move queries µs | Old build bytes | New build bytes |',
         '|---:|---|---:|---:|---:|---:|---:|---:|']
for n in (1000,10000,100000):
    for dist in ('uniform','clustered'):
        m=[value(n,dist,x,'mutation')/1000 for x in ('control','candidate')]
        q=[value(n,dist,x,'mutated') for x in ('control','candidate')]
        a=[value(n,dist,x,'build','median_allocation_bytes') for x in ('control','candidate')]
        text.append(f'| {n:,} | {dist} | {m[0]:.3f} | {m[1]:.3f} | {q[0]:.2f} | {q[1]:.2f} | {a[0]:,.0f} | {a[1]:,.0f} |')
text += ['', '## Method and limits', '',
         'Windows 11 build 26200, Ryzen 9 5950X, .NET SDK 10.0.402/runtime 10.0.13, Rust 1.93.1 MSVC. CPU affinity mask 4, single worker at a time, shared host mutex, tiering disabled. Calibration doubles repetitions to at least 100 ms; one subsequent block is measured. Six fixed-seed fixtures, query widths 0/20/200/1000, five blocks × eight workers × six fixtures = 240 validated process launches. No failed or excluded confirmation samples. Other desktop activity remains uncontrolled; process blocks are descriptive repetitions, not proof of statistical independence.', '',
         'Correctness covers exact result multisets before/after mutation, inclusive edges, duplicates, reference values, extreme finite doubles/subnormals, capacities 4/5/16/128, root collapse, workspace reuse across original/generic implementations, indexed-only input lists, and append semantics. Supplemental interop checks passed for 0/1/16/17 entries in all three modes, including duplicate bounds, negative coordinates, and edge contacts; their timings are excluded. The comparisons use integer-valued geometry represented exactly as double. Rankings do not establish a universal fastest index, nor characterize continuous random coordinates, sustained update-heavy workloads, other capacities, platforms, or large user payloads.', '',
         'DotNetLab was applied after the algorithm commit. CPU captures and full optimized JIT listings guided representation, copy, sorting, and predicate changes. Diagnostic targets were separate from timed workers. The ordinary external target does not qualify for DotNetLab’s native promotion lane; adoption rests on the reproducible normal-build external comparison. Candidate ledger, rejected experiments, capture IDs, source findings, and artifacts: [research record](../Research/2026-10-17-mutable-packed/REPORT.md).', '',
         'Reproduction: stage the pinned Rust sources under a designated task workspace; use `mutable-packed/native.ps1` to fetch, inspect dependencies, and build. Preserve the control library with its original source, build both managed workers using `mutable-packed/locked.ps1`, run action `confirmation`, then execute `mutable-packed/summarize.py`. The checked-in protocol identifies binary hashes, exact launch order, calibration, and environment. Scratch paths are disposable; source, scripts, and evidence remain in this repository.', '']
(base / 'MUTABLE-PACKED.md').write_text('\n'.join(text), encoding='utf-8')
