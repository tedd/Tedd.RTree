"""Publish eight independently executed libraries; never merge different fixture generators."""
import csv, html, json, re
from pathlib import Path
from capabilities import capabilities, render

root=Path(__file__).resolve().parents[2]
folder=root/'benchmarks/results/csharp-charts'
managed=list(csv.DictReader((folder/'summary.csv').open()))
native=list(csv.DictReader((root/'benchmarks/results/mutation-regressions/cross/summary.csv').open()))
labels={'candidate':'Tedd.RTree (C#)','rbush':'RBush (C#)','nts':'NTS STRtree (C#)','rtree':'RTree (C#)','enyim':'Enyim RTree (C#)',
        'static':'static_aabb2d_index (Rust)','geo-hilbert':'geo-index Hilbert (Rust)','geo-str':'geo-index STR (Rust)'}
versions={'candidate':'source af521db / NuGet 1.0.14','rbush':'4.0.0','nts':'2.6.0','rtree':'1.1.0','enyim':'1.0.5','static':'2.1.0','geo-hilbert':'0.4.0','geo-str':'0.4.0'}
results=[]
for size in (1000,10000,100000):
    for distribution in ('uniform','clustered'):
        for operation in ('build','queries'):
            for library,label in labels.items():
                is_native=library in ('static','geo-hilbert','geo-str')
                modes=['native-'+library,'interop-'+library] if is_native else ['nts-list','nts-visitor'] if library=='nts' else [library]
                candidates=[r for r in (native if is_native else managed) if (int(r['size']),r['distribution'],r['operation'])==(size,distribution,operation) and r['library'] in modes]
                assert len(candidates)==len(modes),(size,distribution,operation,library)
                selected=min(candidates,key=lambda r:float(r['median_us']))
                results.append(dict(size=size,distribution=distribution,operation=operation,library=library,label=label,
                    medianUs=float(selected['median_us']),minUs=float(selected['min_us']),maxUs=float(selected['max_us']),mode=selected['library'],
                    record='mutation-regressions/cross' if is_native else 'csharp-charts'))
assert len(results)==96
payload=dict(date='2026-10-18',libraries=versions,records=['csharp-charts','mutation-regressions/cross'],capabilities=capabilities,results=results)
(root/'site/assets/spatial-comparison.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf8',newline='\n')

def subset(size,distribution,operation):
    return sorted((r for r in results if (r['size'],r['distribution'],r['operation'])==(size,distribution,operation)),key=lambda r:r['medianUs'])
section='''    <section class="section-shell benchmark-section" id="benchmarks">
      <div class="section-intro">
        <div><p class="eyebrow">Eight spatial indexes · C# and Rust</p><h2>Mutable tree. Packed-index performance.</h2></div>
        <p>Tedd.RTree is a C# spatial indexing library for .NET 10. It organizes 2D rectangles and 3D boxes so applications can quickly find objects that overlap a search region, while supporting individual inserts, removals, and moves.</p>
      </div>
      <div class="benchmark-controls"><label for="comparison-fixture">Chart fixture</label><select id="comparison-fixture">'''
for size in (100000,10000,1000):
    for distribution in ('uniform','clustered'):
        section+=f'<option value="{size}/{distribution}">{size:,} · {distribution}</option>'
section+='</select><span>Five fresh processes per variant and fixture · median timings · all result IDs validated</span></div>\n      <div class="chart-grid" aria-live="polite">\n'
for operation,title,unit in (('build','Build throughput','M entries/s'),('queries','Query throughput','M windows/s')):
    selected=subset(100000,'uniform',operation)
    units=100000 if operation=='build' else 64
    peak=units/selected[0]['medianUs']
    section+=f'<figure class="bar-chart package-chart" data-operation="{operation}"><figcaption><span data-fixture>100,000 uniform rectangles</span><strong>{title}</strong><small>{unit} · higher is better</small></figcaption><div class="package-chart-rows">\n'
    for r in selected:
        own=r['library']=='candidate';rate=units/r['medianUs']
        value=f'{rate:.3g}' if rate < 0.001 else f'{rate:.3f}'
        section+=f'<div class="bar-row{" comparison-ours" if own else ""}"><span>{html.escape(r["label"])}</span><div class="bar-track"><i class="bar {"ours" if own else "other"}" style="width:{rate/peak*100:.2f}%"></i></div><b>{value}</b></div>\n'
    section+='</div></figure>\n'
section+='</div>\n'+render(results)
section+='''
      <div class="results-panel"><div class="results-heading"><h3>All measured fixtures</h3><p>Median elapsed time · lower is better</p></div><div class="table-scroll"><table class="package-results"><caption>Eight-library 2D comparison, measured 18 October 2026</caption><thead><tr><th scope="col">Entries</th><th scope="col">Distribution</th><th scope="col">Operation</th>'''
section+=''.join(f'<th scope="col">{html.escape(label)}</th>' for label in labels.values())+'</tr></thead><tbody>\n'
for size in (1000,10000,100000):
    for distribution in ('uniform','clustered'):
        for operation in ('build','queries'):
            selected=subset(size,distribution,operation)
            section+=f'<tr><th scope="row">{size:,}</th><td>{distribution.title()}</td><td>{"Construction" if operation=="build" else "64 queries"}</td>'
            for library in labels:
                r=next(r for r in selected if r['library']==library)
                classes=('comparison-ours ' if library=='candidate' else '')+('best' if r==selected[0] else '')
                time=f'{r["medianUs"]/1000:.3f} ms' if operation=='build' else f'{r["medianUs"]:.2f} µs'
                section+=f'<td class="{classes}">{time}</td>'
            section+='</tr>\n'
section+='''</tbody></table></div></div>
      <p class="benchmark-method">18 October 2026 · Ryzen 9 5950X · Windows 11 · .NET 10.0.13 · Rust 1.93.1 · one CPU affinity · node capacity 16. Six deterministic 2D fixtures; 64 windows with widths 0, 20, 200 and 1,000. Five fresh-process blocks per variant, calibrated to at least 100 ms. Every returned ID is consumed. Aggregate medians use each process’s sum of four query groups. C# and Rust measurements come from separate sessions with identical geometry and runtime settings; the records include ranges and source identities.</p>
      <p class="benchmark-method">Each library runs independently. Tedd reuses a result list. RBush 4.0.0, NTS 2.6.0 and Enyim 1.0.5 use bulk construction; RTree 1.1.0 uses incremental insertion with exact float coordinates at z = 0. NTS receives its better whole-workload median from list and reusable visitor queries. Enyim’s published .NET Framework binary is measured as distributed, including its disabled optimizations. NTS STRtree and the Rust indexes do not accept inserts after construction.</p>
      <p class="benchmark-method">Rust builds use native CPU optimization, thin LTO, and preallocated scratch/output where supported. Each Rust score is the lower whole-workload median of direct execution and optimized interop. Short, allocation-free interop calls suppress GC transitions; direct Rust removes interop entirely. Native builds include destruction; managed reclamation occurs through GC. SharpTrees 1.0.6 is unranked because its result IDs fail validation.</p>
      <p class="benchmark-method">Tedd.RTree supports individual inserts, removals, and moves after bulk loading. The comparison records include managed allocation, ranges and mutation measurements. These fixtures describe specific workloads rather than a universal fastest index.</p>
      <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CSHARP-CHARTS.md">C# methods, versions and full measurements ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/MUTABLE-PACKED.md">Rust methods, ranges and pinned sources ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/results/csharp-charts/summary.csv">C# timing CSV ↗</a><a href="assets/spatial-comparison.json">Chart data ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CROSS-LANGUAGE.md">C, C++, Go and JavaScript screening ↗</a></div>

'''
page=root/'site/index.html'
source=page.read_text(encoding='utf8')
start=source.index('    <section class="section-shell benchmark-section"')
end=source.index('      <div class="coordinate-benchmark"',start)
source=source[:start]+section+source[end:]
build=next(r['medianUs'] for r in results if (r['size'],r['distribution'],r['operation'],r['library'])==(100000,'uniform','build','candidate'))/1000
query=next(r['medianUs'] for r in results if (r['size'],r['distribution'],r['operation'],r['library'])==(100000,'uniform','queries','candidate'))
hero=f'        <p class="hero-evidence">For 100,000 uniform 2D rectangles, Tedd.RTree bulk loading takes <strong>{build:.3f} ms</strong> and 64 queries take <strong>{query:.2f} µs</strong>. <a href="#benchmarks">Compare eight C# and Rust indexes</a>.</p>'
source=re.sub(r'        <p class="hero-evidence"[^>]*>.*?</p>',lambda _:hero,source,count=1)
source=source.replace('app.js?v=cf34a58','app.js?v=csharp-eight').replace('styles.css?v=cf34a58','styles.css?v=csharp-eight')
source=source.replace('app.js?v=csharp-eight','app.js?v=capabilities-1').replace('styles.css?v=csharp-eight','styles.css?v=capabilities-1')
source=source.replace('Compare Tedd.RTree (C#), static_aabb2d_index (Rust), and geo-index (Rust) on six published fixtures.','Compare eight C# and Rust spatial indexes on six published fixtures.')
page.write_text(source,encoding='utf8',newline='\n')
record=['# C# libraries in the shared 2D comparison','',
    'Measured 18 October 2026. All five C# chart scores use this complete fresh 180-process record. The three Rust scores retain the separate same-day [optimized direct/interop record](MUTABLE-PACKED.md). Geometry, runtime and timing settings match; sessions were not interleaved. No rescaling or selection between old/new Tedd timings is performed. Small differences need further measurement.','',
    '## APIs and construction','',
    '| Library | Version | Construction / query API |','|---|---|---|',
    '| Tedd.RTree | Source af521db (NuGet 1.0.14 code) | BulkLoad; reused result list |',
    '| RBush | 4.0.0 | BulkLoad; Search collection |',
    '| NTS STRtree | 2.6.0 | Insert batch + Build; better median of Query list / reusable IItemVisitor |',
    '| RTree | 1.1.0 | Incremental Add; Intersects collection; exact float z=0 embedding |',
    '| Enyim RTree | 1.0.5 | Load with fresh working list; Search collection; published binary |','',
    'NTS does not accept inserts after construction. Enyim targets .NET Framework and its published binary disables optimizations; NU1701 is expected. The runtime checks establish tested behavior on .NET 10, not general compatibility. SharpTrees 1.0.6 remains excluded for an existing exact-ID correctness failure. Benchmark packages are not dependencies of the shipped library. Official core paths and package build hooks were inspected before execution; [provenance](../Research/2026-10-18-csharp-charts/provenance.json) records package/source hashes and limitations.','',
    '## Chart measurements','',
    '| Entries | Distribution | Library | Build ms | Mode | 64 queries µs | Mode |','|---:|---|---|---:|---|---:|---|']
for n in (1000,10000,100000):
    for distribution in ('uniform','clustered'):
        for library,label in labels.items():
            b=next(r for r in results if (r['size'],r['distribution'],r['library'],r['operation'])==(n,distribution,library,'build'))
            q=next(r for r in results if (r['size'],r['distribution'],r['library'],r['operation'])==(n,distribution,library,'queries'))
            record.append(f'| {n:,} | {distribution} | {label} | {b["medianUs"]/1000:.3f} | {b["mode"]} | {q["medianUs"]:.2f} | {q["mode"]} |')
record+=['','## Method and limits','',
    'Ryzen 9 5950X, Windows 11, SDK 10.0.402/CoreCLR 10.0.13, Release x64, tiering disabled, affinity mask 4, capacity 16. Five shuffled fresh processes for every mode/fixture, seed 49217. Each operation calibrates to at least 100ms and measures one block. Construction precedes four query-width groups; the sum within each process forms its 64-query observation. The LCG seed 73211 and exact file bytes match the Rust fixture; this is not the older System.Random BenchmarkDotNet fixture. Geometry and item/query adapters are prepared before timing. Construction includes each API’s required working copies. Every returned ID is consumed, including visitor callbacks, rather than merely counting matching nodes.','',
    'All 180 processes check exact sorted result IDs against independent brute-force scans and check the timed checksum for every window before timing. All 24 empty/negative/contact/duplicate/reversed-input boundary cases pass. The sum visitor is reused and does not materialize a result list; allocating collection APIs retain their native allocation. This comparison includes those public API differences. No competitor implementation is rewritten.','',
    'Medians and min/max describe five process blocks. Fresh PIDs do not establish statistical independence; desktop activity, thermal/frequency variation and GC remain uncontrolled. Native and managed rows are separate sessions, not a paired statistical experiment. No significance, universal fastest ranking or tail latency is claimed. Current-thread allocation is not retained memory or working set. NTS and Rust selection uses complete mode medians per operation, never favorable individual samples.','',
    'The [contemporaneous Tedd reference](results/csharp-charts/tedd-reference.json) reports its complete fresh/previous ratios without normalization; earlier data remain unchanged. [Protocol](../Research/2026-10-18-csharp-charts/PROTOCOL.md), [full timing/allocation/ranges](results/csharp-charts/summary.csv), [raw observations](results/csharp-charts/samples.json), [process identities](results/csharp-charts/processes.json), [boundary results](results/csharp-charts/boundaries.json), [worker](csharp-charts/Worker.cs).','',
    'Reproduce in a dedicated task workspace: run `benchmarks/csharp-charts/locked.ps1 build`, then `measure`, `summarize.py` and `export.py`. All builds/measurements hold the shared performance mutex. Inspect package sources and execution paths before running; cleanup removes only owned disposable artifacts after shutdown.','']
(root/'benchmarks/CSHARP-CHARTS.md').write_text('\n'.join(record),encoding='utf8',newline='\n')
print('Published 96 chart observations across eight libraries, six fixtures and two operations.')
