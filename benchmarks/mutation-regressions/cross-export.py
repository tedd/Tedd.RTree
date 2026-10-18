"""Export the current confirmation results and static, accessible site fallback."""
import csv
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
rows = list(csv.DictReader((root / 'benchmarks/results/mutation-regressions/cross/summary.csv').open()))
labels = {'candidate': 'Tedd.RTree (C#)', 'static': 'static_aabb2d_index (Rust)',
          'geo-hilbert': 'geo-index Hilbert (Rust)', 'geo-str': 'geo-index STR (Rust)'}
results = []
for size in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        for operation in ('build', 'queries'):
            for library, label in labels.items():
                modes = [library] if library == 'candidate' else ['native-' + library, 'interop-' + library]
                candidates = [r for r in rows if int(r['size']) == size and r['distribution'] == distribution
                              and r['operation'] == operation and r['library'] in modes]
                selected = min(candidates, key=lambda r: float(r['median_us']))
                results.append(dict(size=size, distribution=distribution, operation=operation, library=library,
                                    label=label, medianUs=float(selected['median_us']), minUs=float(selected['min_us']),
                                    maxUs=float(selected['max_us']), mode=selected['library']))
(root / 'site/assets/mutable-packed.json').write_text(json.dumps(dict(date='2026-10-18', source=sys.argv[1], results=results), indent=2) + '\n')

def subset(size, distribution, operation):
    return sorted((r for r in results if (r['size'], r['distribution'], r['operation']) == (size, distribution, operation)), key=lambda r: r['medianUs'])

section = '''    <section class="section-shell benchmark-section" id="benchmarks">
      <div class="section-intro">
        <div><p class="eyebrow">C# and Rust · identical geometry</p><h2>Mutable tree. Packed-index performance.</h2></div>
        <p>Tedd.RTree is a C# spatial indexing library for .NET 10. It organizes 2D rectangles and 3D boxes so applications can quickly find objects that overlap a search region, while supporting individual inserts, removals, and moves.</p>
      </div>
      <div class="benchmark-controls"><label for="comparison-fixture">Chart fixture</label><select id="comparison-fixture">'''
for size in (100000, 10000, 1000):
    for distribution in ('uniform', 'clustered'):
        section += f'<option value="{size}/{distribution}">{size:,} · {distribution}</option>'
section += '</select><span>Five fresh processes per variant and fixture · median timings · all result IDs validated</span></div>\n      <div class="chart-grid" aria-live="polite">\n'
for operation, title, unit in (('build', 'Build throughput', 'M entries/s'), ('queries', 'Query throughput', 'M windows/s')):
    selected = subset(100000, 'uniform', operation)
    units = 100000 if operation == 'build' else 64
    peak = units / selected[0]['medianUs']
    section += f'<figure class="bar-chart package-chart" data-operation="{operation}"><figcaption><span data-fixture>100,000 uniform rectangles</span><strong>{title}</strong><small>{unit} · higher is better</small></figcaption><div class="package-chart-rows">\n'
    for r in selected:
        own = r['library'] == 'candidate'
        rate = units / r['medianUs']
        section += f'<div class="bar-row{" comparison-ours" if own else ""}"><span>{r["label"]}</span><div class="bar-track"><i class="bar {"ours" if own else "other"}" style="width:{rate / peak * 100:.2f}%"></i></div><b>{rate:.3f}</b></div>\n'
    section += '</div></figure>\n'
section += '''</div>
      <div class="results-panel"><div class="results-heading"><h3>All measured fixtures</h3><p>Median elapsed time · lower is better</p></div><div class="table-scroll"><table class="package-results"><caption>Current mutable-tree and Rust comparison, measured 18 October 2026</caption><thead><tr><th scope="col">Entries</th><th scope="col">Distribution</th><th scope="col">Operation</th>'''
section += ''.join(f'<th scope="col">{label}</th>' for label in labels.values()) + '</tr></thead><tbody>\n'
for size in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        for operation in ('build', 'queries'):
            selected = subset(size, distribution, operation)
            section += f'<tr><th scope="row">{size:,}</th><td>{distribution.title()}</td><td>{"Bulk build" if operation == "build" else "64 queries"}</td>'
            for library in labels:
                r = next(r for r in selected if r['library'] == library)
                classes = ('comparison-ours ' if library == 'candidate' else '') + ('best' if r == selected[0] else '')
                time = f'{r["medianUs"] / 1000:.3f} ms' if operation == 'build' else f'{r["medianUs"]:.2f} µs'
                section += f'<td class="{classes}">{time}</td>'
            section += '</tr>\n'
section += '''</tbody></table></div></div>
      <p class="benchmark-method">18 October 2026 · Ryzen 9 5950X · Windows 11 · .NET 10.0.13 · Rust 1.93.1 · one CPU affinity · node capacity 16. Six deterministic fixtures; 64 windows with widths 0, 20, 200 and 1,000. Five fresh-process blocks per variant, calibrated to at least 100 ms. Queries materialize and consume every result ID. Tedd reuses a result list. Aggregate medians are computed from each process’s sum of four query groups.</p>
      <p class="benchmark-method">Each library runs independently. Rust builds use native CPU optimization, thin LTO, and preallocated scratch/output where supported. Each Rust score is the lower whole-workload median of direct execution and optimized interop. Short, allocation-free interop calls suppress GC transitions; direct Rust removes interop entirely. Rust indexes are immutable; Tedd supports inserts, removals, and moves after bulk loading. Native builds include destruction; managed reclamation occurs through GC.</p>
      <p class="benchmark-method">Tedd.RTree retains individual inserts, removals, and moves after bulk loading. The comparison record includes update batches, queries after updates, allocation, ranges, and source identities. These fixtures describe specific workloads rather than a universal fastest index.</p>
      <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/MUTABLE-PACKED.md">Method, ranges and pinned sources ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/results/mutation-regressions/cross/summary.csv">Full timing CSV ↗</a><a href="assets/mutable-packed.json">Chart data ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CROSS-LANGUAGE.md">Earlier C, C++, Go and JavaScript screening ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/PACKAGE-COMPARISON.md">Earlier .NET package comparison ↗</a></div>

'''
page = root / 'site/index.html'
html = page.read_text(encoding='utf-8')
start = html.index('    <section class="section-shell benchmark-section"')
end = html.index('      <div class="coordinate-benchmark"', start)
page.write_text(html[:start] + section + html[end:], encoding='utf-8', newline='\n')

html=page.read_text(encoding='utf8')
hero=list(re.finditer(r'        <p class="hero-evidence"[^>]*>.*?</p>',html))[0]
build=next(r['medianUs'] for r in results if (r['size'],r['distribution'],r['operation'],r['library'])==(100000,'uniform','build','candidate'))/1000
query=next(r['medianUs'] for r in results if (r['size'],r['distribution'],r['operation'],r['library'])==(100000,'uniform','queries','candidate'))
hero_text=f'        <p class="hero-evidence">For 100,000 uniform 2D rectangles, Tedd.RTree bulk loading takes <strong>{build:.3f} ms</strong> and 64 queries take <strong>{query:.2f} µs</strong>. <a href="#benchmarks">See the cross-language measurements</a>.</p>'
page.write_text(html[:hero.start()]+hero_text+html[hero.end():],encoding='utf8',newline='\n')
