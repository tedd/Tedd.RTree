"""Export the current confirmation results and static, accessible site fallback."""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
rows = list(csv.DictReader((root / 'benchmarks/results/mutable-packed/confirmation/summary.csv').open()))
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
(root / 'site/assets/mutable-packed.json').write_text(json.dumps(dict(date='2026-10-17', source='a5d902c', results=results), indent=2) + '\n')

def subset(size, distribution, operation):
    return sorted((r for r in results if (r['size'], r['distribution'], r['operation']) == (size, distribution, operation)), key=lambda r: r['medianUs'])

section = '''    <section class="section-shell benchmark-section" id="benchmarks">
      <div class="section-intro">
        <div><p class="eyebrow">C# and Rust · identical geometry</p><h2>Mutable tree. Packed-index performance.</h2></div>
        <p>Bulk construction and 64 intersection queries against two fast Rust indexes. Teal identifies Tedd.RTree. Higher bars mean greater throughput. Language appears after each library name.</p>
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
      <div class="results-panel"><div class="results-heading"><h3>All measured fixtures</h3><p>Median elapsed time · lower is better</p></div><div class="table-scroll"><table class="package-results"><caption>Current mutable-tree and Rust comparison, measured 17 October 2026</caption><thead><tr><th scope="col">Entries</th><th scope="col">Distribution</th><th scope="col">Operation</th>'''
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
      <p class="benchmark-method">17 October 2026 · Ryzen 9 5950X · Windows 11 · .NET 10.0.13 · Rust 1.93.1 · one CPU affinity · node capacity 16. Six deterministic fixtures; 64 windows with widths 0, 20, 200 and 1,000. Five fresh-process blocks per variant, calibrated to at least 100 ms. Queries materialize and consume every result ID. Tedd reuses a result list. Aggregate medians are computed from each process’s sum of four query groups.</p>
      <p class="benchmark-method">Competitors receive native CPU optimization, thin LTO, and preallocated scratch/output where their APIs permit. Each cell uses the lower whole-workload median of direct Rust and optimized interop execution. Short, allocation-free interop calls suppress GC transitions; direct Rust removes interop entirely. Rust indexes are immutable; Tedd supports inserts, removals, and moves after bulk loading. Native builds include destruction; managed reclamation occurs through GC.</p>
      <p class="benchmark-method">At 100,000 entries, bulk loading is 4.18–4.40× faster and aggregate queries 1.72–2.01× faster than the previous Tedd implementation. Tedd has the lowest aggregate query median in five of six fixtures; the 10,000-uniform margin is only about 1%. Static-index selective queries can be faster. Measured move batches regressed by up to 14%; post-move queries improved in every fixture. These fixtures do not establish a universal fastest index or steady-state update throughput.</p>
      <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/MUTABLE-PACKED.md">Method, ranges and pinned sources ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/results/mutable-packed/confirmation/summary.csv">Full timing CSV ↗</a><a href="assets/mutable-packed.json">Chart data ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CROSS-LANGUAGE.md">Earlier C, C++, Go and JavaScript screening ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/PACKAGE-COMPARISON.md">Earlier .NET package comparison ↗</a></div>

'''
page = root / 'site/index.html'
html = page.read_text(encoding='utf-8')
start = html.index('    <section class="section-shell benchmark-section"')
end = html.index('      <div class="coordinate-benchmark">', start)
page.write_text(html[:start] + section + html[end:], encoding='utf-8', newline='\n')
