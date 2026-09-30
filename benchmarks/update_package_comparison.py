"""Generate the public comparison from a completed BenchmarkDotNet JSON export.

Usage: python benchmarks/update_package_comparison.py <full-compressed.json>
"""
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = ["Tedd.RTree", "RBush", "NetTopologySuite", "RTree", "Enyim.Collections.RTree"]
LABELS = {"NetTopologySuite": "NTS STRtree", "Enyim.Collections.RTree": "Enyim RTree"}
VERSIONS = {"Tedd.RTree": "local source", "RBush": "4.0.0", "NetTopologySuite": "2.6.0", "RTree": "1.1.0", "Enyim.Collections.RTree": "1.0.5"}


def load(path):
    report = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    results = []
    for b in report["Benchmarks"]:
        params = dict(part.split("=", 1) for part in b["Parameters"].split("&"))
        # BenchmarkDotNet shortens long parameter strings in its standard exports.
        if params["Library"] == "Enyim(...)RTree [23]":
            params["Library"] = "Enyim.Collections.RTree"
        stats = b["Statistics"]
        if stats is None:
            raise ValueError(f"Missing measurement: {b['DisplayInfo']}")
        results.append({"size": int(params["Size"]), "distribution": params["Distribution"].strip(),
                        "library": params["Library"].strip(), "operation": b["Method"],
                        "meanNs": stats["Mean"], "stdDevNs": stats["StandardDeviation"],
                        "allocatedBytes": b["Memory"]["BytesAllocatedPerOperation"]})
    expected = {(s, d, l, o) for s in (1000, 10000) for d in ("Uniform", "Clustered")
                for l in LIBRARIES for o in ("Build", "Query64")}
    actual = {(r["size"], r["distribution"], r["library"], r["operation"]) for r in results}
    if actual != expected or len(results) != len(expected):
        raise ValueError("Expected exactly 40 complete benchmark results")
    return report, results


def chart(results, operation):
    rows = sorted((r for r in results if r["size"] == 10000 and r["distribution"] == "Uniform" and r["operation"] == operation), key=lambda r: r["meanNs"])
    # Build throughput is entries/s; query throughput is windows/s, not matched items/s.
    units = 10000 if operation == "Build" else 64
    peak = units * 1e9 / rows[0]["meanNs"]
    title = "Build throughput" if operation == "Build" else "Query throughput"
    unit = "M entries/s" if operation == "Build" else "M windows/s"
    text = [f'<figure class="bar-chart package-chart" data-operation="{operation}"><figcaption><span data-fixture>10,000 uniform rectangles</span><strong>{title}</strong><small>{unit} · higher is better</small></figcaption><div class="package-chart-rows">']
    for r in rows:
        rate = units * 1e9 / r["meanNs"]
        own = r["library"] == "Tedd.RTree"
        text.append(f'<div class="bar-row{" comparison-ours" if own else ""}"><span>{html.escape(LABELS.get(r["library"], r["library"]))}</span><div class="bar-track"><i class="bar {"ours" if own else "other"}" style="width:{rate / peak * 100:.2f}%"></i></div><b>{rate / 1e6:.3f}</b></div>')
    text.append('</div></figure>')
    return "\n".join(text)


def table(results):
    text = ['<div class="results-panel"><div class="results-heading"><h3>All measured fixtures</h3><p>Mean ± sample standard deviation · managed allocation per operation</p></div><div class="table-scroll"><table class="package-results"><caption>Build and query time across five validated R-tree packages</caption><thead><tr><th scope="col">Entries</th><th scope="col">Distribution</th><th scope="col">Operation</th>']
    text.extend(f'<th scope="col">{html.escape(LABELS.get(l, l))}</th>' for l in LIBRARIES)
    text.append('</tr></thead><tbody>')
    for operation in ("Build", "Query64"):
        for size in (1000, 10000):
            for distribution in ("Uniform", "Clustered"):
                rows = {r["library"]: r for r in results if r["size"] == size and r["distribution"] == distribution and r["operation"] == operation}
                best = min(r["meanNs"] for r in rows.values())
                divider = ' class="table-divider"' if operation == "Query64" and size == 1000 and distribution == "Uniform" else ''
                text.append(f'<tr{divider}><th scope="row">{size:,}</th><td>{distribution}</td><td>{"Build" if operation == "Build" else "64 queries"}</td>')
                divisor, unit = (1e6, "ms") if operation == "Build" else (1e3, "µs")
                for library in LIBRARIES:
                    r = rows[library]
                    classes = []
                    if library == "Tedd.RTree": classes.append("comparison-ours")
                    if r["meanNs"] == best: classes.append("best")
                    text.append(f'<td class="{" ".join(classes)}">{r["meanNs"] / divisor:.3f} ± {r["stdDevNs"] / divisor:.3f} {unit}<small>{r["allocatedBytes"] / 1024:,.2f} KiB allocated</small></td>')
                text.append('</tr>')
    text.append('</tbody></table></div></div>')
    return "\n".join(text)


def main():
    report, results = load(sys.argv[1])
    payload = {"date": "2026-09-30", "libraries": VERSIONS, "results": results}
    target = ROOT / "site/assets/package-comparison.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    comparison = '''      <div class="section-intro">
        <div><p class="eyebrow">Five validated packages · .NET 10</p><h2>R-tree package comparison.</h2></div>
        <p>Build and intersection-query throughput on identical rectangles. Teal identifies Tedd.RTree; grey identifies competing packages. Higher bars mean more work per second. Each query creates its result collection.</p>
      </div>
      <div class="benchmark-controls"><label for="comparison-fixture">Chart fixture</label><select id="comparison-fixture"><option value="10000/Uniform">10,000 · uniform</option><option value="10000/Clustered">10,000 · clustered</option><option value="1000/Uniform">1,000 · uniform</option><option value="1000/Clustered">1,000 · clustered</option></select><span>Tables show every fixture. Bold times mark the lowest measured mean.</span></div>
      <div class="chart-grid" id="package-charts" aria-live="polite">
''' + chart(results, "Build") + "\n" + chart(results, "Query64") + "\n      </div>\n" + table(results) + '''
      <p class="benchmark-method">30 September 2026 · AMD Ryzen 9 5950X · Windows 11 · .NET 10.0.12 · BenchmarkDotNet 0.15.8 · one launch, three warm-ups and three measured iterations. Fixed seed 73211; integer-valued bounds; 64 windows with widths 0, 20, 200 and 1,000 units. Input geometry and package adapters are prepared outside timing. Every query's result IDs are checked against brute force before measurement. These results describe this fixture; small differences require further measurement.</p>
      <p class="benchmark-method">Tedd.RTree, RBush 4.0.0, Enyim.Collections.RTree 1.0.5 and NetTopologySuite 2.6.0 use bulk construction. RTree 1.1.0 uses incremental insertion, with the 2D data embedded at z = 0 in its 3D float index. Node capacity is 16. STRtree does not accept inserts after build. Enyim targets .NET Framework and its published binary has optimizations disabled; it passed the .NET 10 checks and is measured as distributed. The concurrent wrappers have <a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/CONCURRENCY.md">separate measurements</a>.</p>
      <div class="comparison-exclusion"><strong>SharpTrees 1.0.6: excluded from timing</strong><p>Its first uniform 1,000-entry validation returned 39 matches where brute force found 40, omitting ID 942. The package is included in the reproducible validation probe, but incorrect result sets are not ranked as faster queries.</p></div>
      <div class="evidence-links"><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/PACKAGE-COMPARISON.md">Method, package list and validation ↗</a><a href="https://github.com/tedd/Tedd.RTree/blob/main/benchmarks/results/package-comparison/PackageComparisonBenchmarks-report.csv">Raw BenchmarkDotNet CSV ↗</a><a href="assets/package-comparison.json">Chart data ↗</a></div>

'''
    page = ROOT / "site/index.html"
    source = page.read_text(encoding="utf-8")
    uniform = {(r["library"], r["operation"]): r["meanNs"] for r in results
               if r["size"] == 10000 and r["distribution"] == "Uniform"}
    hero = (f'In the measured 10,000-entry uniform fixture, bulk build took <strong>{uniform["Tedd.RTree", "Build"]/1e6:.2f} ms</strong> '
            f'versus {uniform["RBush", "Build"]/1e6:.2f} ms for RBush and {uniform["NetTopologySuite", "Build"]/1e6:.2f} ms for NTS STRtree. '
            f'A batch of 64 queries took <strong>{uniform["Tedd.RTree", "Query64"]/1e3:.2f} µs</strong> '
            f'versus {uniform["RBush", "Query64"]/1e3:.2f} µs and {uniform["NetTopologySuite", "Query64"]/1e3:.2f} µs. '
            '<a href="#benchmarks">See all five packages and benchmark conditions</a>.')
    source = re.sub(r'(<p class="hero-evidence">).*?(</p>)', lambda m: m[1] + hero + m[2], source, flags=re.S)
    start = source.index('      <div class="section-intro">', source.index('id="benchmarks"'))
    end = source.index('      <div class="coordinate-benchmark">', start)
    page.write_text(source[:start] + comparison + source[end:], encoding="utf-8", newline="\n")
    rows = []
    for r in sorted(results, key=lambda r: (r["size"], r["distribution"], r["operation"], r["library"])):
        divisor, unit = (1e6, "ms") if r["operation"] == "Build" else (1e3, "µs")
        rows.append(f'| {r["size"]:,} | {r["distribution"]} | {r["operation"]} | {r["library"]} | {r["meanNs"]/divisor:.3f} ± {r["stdDevNs"]/divisor:.3f} {unit} | {r["allocatedBytes"]/1024:.2f} KiB |')
    record = ROOT / "benchmarks/PACKAGE-COMPARISON.md"
    source = record.read_text(encoding="utf-8")
    start, end = source.index('<!-- results:start -->'), source.index('<!-- results:end -->')
    record.write_text(source[:start] + '<!-- results:start -->\n\n| Entries | Distribution | Operation | Package | Mean ± standard deviation | Allocated |\n|---:|---|---|---|---:|---:|\n' + '\n'.join(rows) + '\n\n' + source[end:], encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
