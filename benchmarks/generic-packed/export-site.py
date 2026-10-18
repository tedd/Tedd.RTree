"""Export only completed confirmation data; retain static charts when scripting is disabled."""
import csv
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
rows = list(csv.DictReader((root/'benchmarks/results/generic-packed/confirmation/summary.csv').open()))
results = []
for row in rows:
    if row['operation'] not in ('build','queries'): continue
    results.append(dict(dimension=int(row['dimension']),coordinate=row['coordinate'],size=int(row['size']),
                        distribution=row['distribution'],mode=row['mode'],stage=row['stage'],operation=row['operation'],
                        medianUs=float(row['median_us']),minUs=float(row['min_us']),maxUs=float(row['max_us'])))
(root/'site/assets/generic-packed.json').write_text(json.dumps(dict(date='2026-10-18',control='3d2d88f',candidate='04028ea',results=results),indent=2)+'\n')

def value(dim,coordinate,size,distribution,mode,stage,operation):
    return next(r['medianUs'] for r in results if (r['dimension'],r['coordinate'],r['size'],r['distribution'],r['mode'],r['stage'],r['operation']) == (dim,coordinate,size,distribution,mode,stage,operation))

section = '''      <div class="coordinate-benchmark" id="generic-benchmarks">
        <h3>2D and 3D API performance</h3>
        <p>Compare the current implementation with the previous release on identical geometry. Plain trees, snapshots, and concurrent indexes support all four coordinate types. Select an API and workload to see its measured construction and search throughput.</p>
        <div class="benchmark-controls generic-controls">
          <div><label for="generic-dimension">Dimension</label><select id="generic-dimension"><option value="3">3D</option><option value="2">2D</option></select></div>
          <div><label for="generic-coordinate">Coordinates</label><select id="generic-coordinate"><option>double</option><option>float</option><option>int</option><option>long</option></select></div>
          <div><label for="generic-mode">API</label><select id="generic-mode"><option value="plain">Plain mutable</option><option value="snapshot">Snapshot</option><option value="concurrent">Concurrent</option></select></div>
          <div><label for="generic-fixture">Workload</label><select id="generic-fixture"><option value="100000/uniform">100,000 · uniform</option><option value="100000/clustered">100,000 · clustered</option><option value="10000/uniform">10,000 · uniform</option><option value="10000/clustered">10,000 · clustered</option></select></div>
        </div>
        <p class="benchmark-method" id="generic-scope">Plain mutable APIs: 10,000 and 100,000 entries, uniform and clustered. Snapshot and concurrent measurements: 10,000 uniform entries.</p>
        <div class="chart-grid" aria-live="polite">
'''
for operation,title,unit in (('build','Build throughput','M entries/s'),('queries','Query throughput','M windows/s')):
    selected = [(stage,value(3,'double',100000,'uniform','plain',stage,operation)) for stage in ('control','candidate')]
    selected.sort(key=lambda r:r[1]);units=100000 if operation=='build' else 64;peak=units/selected[0][1]
    section+=f'<figure class="bar-chart generic-chart" data-operation="{operation}"><figcaption><span data-generic-fixture>3D double · 100,000 uniform entries · plain</span><strong>{title}</strong><small>{unit} · higher is better</small></figcaption><div class="generic-chart-rows">\n'
    for stage,time in selected:
        rate=units/time;label='Current (C#)' if stage=='candidate' else 'Previous (C#)'
        section+=f'<div class="bar-row{" comparison-ours" if stage=="candidate" else ""}"><span>{label}</span><div class="bar-track"><i class="bar {"ours" if stage=="candidate" else "other"}" style="width:{rate/peak*100:.2f}%"></i></div><b>{rate:.3f}</b></div>\n'
    section+='</div></figure>\n'
section+='''        </div>
        <div class="results-panel"><div class="results-heading"><h3>Selected workload timings</h3><p>Median of three fresh-process block averages · lower is better</p></div><div class="table-scroll"><table><caption id="generic-caption">3D double · 100,000 uniform entries · plain</caption><thead><tr><th scope="col">Operation</th><th scope="col">Previous release (C#)</th><th scope="col">Current (C#)</th><th scope="col">Speedup</th></tr></thead><tbody id="generic-timings">
'''
for operation,label in (('build','Bulk build'),('queries','64 queries')):
    old,new=[value(3,'double',100000,'uniform','plain',stage,operation) for stage in ('control','candidate')]
    scale,unit=(1000,'ms') if operation=='build' else (1,'µs')
    section+=f'<tr><th scope="row">{label}</th><td>{old/scale:.3f} {unit}</td><td class="comparison-ours">{new/scale:.3f} {unit}</td><td>{old/new:.2f}×</td></tr>\n'
section+='''        </tbody></table></div></div>
        <p class="benchmark-method">18 October 2026 · Ryzen 9 5950X · Windows 11 · .NET 10.0.13 · three fresh-process blocks per variant/workload, fixed shuffled order, one CPU affinity, node capacity 16. Builds use prepared entries; 64 query windows include points, edge contacts, and complete containment. Every returned ID is checked against brute force before timing, and again after moves in mutable APIs. Queries reuse a result list and consume all IDs.</p>
        <p class="benchmark-method">The comparison uses the actual dimension selected; 3D queries test all three axes. Previous release: library source at 3d2d88f, matching NuGet 1.0.8. Snapshot construction includes full-batch publication; concurrent construction and queries include normal locking. These are before/after measurements of Tedd.RTree; the Rust comparison above covers the original 2D API. Precision at extreme coordinates and adjacent long values beyond 2⁵³ is tested separately from the timing fixtures.</p>
        <p class="benchmark-method">Build and aggregate query medians improved in every measured configuration. Updates have a tradeoff: some 10,000-entry clustered move batches were up to 52% slower, while all post-move query aggregates improved. Medians describe these workloads, not universal rankings or tail latency. Mutation timings, allocations, process ranges, source identities, and the 3D ordering tradeoff are available in the full record.</p>
        <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/GENERIC-PACKED.md">All APIs, timings and mutation guardrails ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/results/generic-packed/confirmation/summary.csv">Medians, ranges and allocation CSV ↗</a><a href="assets/generic-packed.json">Chart data ↗</a></div>
      </div>
'''
path=root/'site/index.html';html=path.read_text(encoding='utf8')
hero=list(re.finditer(r'        <p class="hero-evidence"[^>]*>.*?</p>',html))[1]
build=value(3,'double',100000,'uniform','plain','candidate','build')/1000
query=value(3,'double',100000,'uniform','plain','candidate','queries')
old_build=value(3,'double',100000,'uniform','plain','control','build')/1000
old_query=value(3,'double',100000,'uniform','plain','control','queries')
hero_text=f'        <p class="hero-evidence" id="generic-hero-evidence">For 100,000 uniform 3D boxes with <code>double</code> coordinates, bulk loading takes <strong>{build:.3f} ms</strong> and 64 queries take <strong>{query:.2f} µs</strong>, compared with {old_build:.3f} ms and {old_query:.2f} µs in the previous release. <a href="#generic-benchmarks">Explore timings for every coordinate type and API</a>.</p>'
html=html[:hero.start()]+hero_text+html[hero.end():]
start=html.index('      <div class="coordinate-benchmark"')
end=html.index('    </section>',start)
path.write_text(html[:start]+section+html[end:],encoding='utf8',newline='\n')
