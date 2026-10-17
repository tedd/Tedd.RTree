"""Rebuild the report from the primary and supplementary raw process averages."""
import csv
import json
from pathlib import Path
import statistics

benchmarks = Path(__file__).resolve().parents[1]
primary = benchmarks / 'results/cross-language'
supplementary = benchmarks / 'results/cross-language-supplementary'
samples = json.loads((primary / 'samples.json').read_text()) + json.loads((supplementary / 'samples.json').read_text())
libraries = list(dict.fromkeys(s['library'] for s in samples))
order = ['Tedd bulk reused', 'Tedd bulk allocating', 'Tedd incremental', 'Tidwall C', 'Tidwall Go',
         'Superliminal C++', 'Boost.Geometry packed', 'Boost.Geometry visitor', 'rstar bulk',
         'geo-index Hilbert', 'geo-index STR', 'static_aabb2d_index', 'Flatbush']
assert set(libraries) == set(order)
assert len(samples) == 13 * 6 * 5 * 5
assert all(s['microseconds'] > 0 for s in samples)
fixtures = json.loads((primary / 'fixtures.json').read_text())
assert [f['sha256'] for f in fixtures] == [f['sha256'] for f in json.loads((supplementary / 'fixtures.json').read_text())]
summary = {}
aggregate = []
for f in fixtures:
    n, d = f['size'], f['distribution']
    for library in order:
        rows = [s for s in samples if (s['library'], s['size'], s['distribution']) == (library, n, d)]
        assert len(rows) == 25
        for op in ('build', 'query0', 'query1', 'query2', 'query3'):
            values = [s['microseconds'] for s in rows if s['operation'] == op]
            assert len(values) == 5
            assert len({s['round'] for s in rows if s['operation'] == op}) == 5
            summary[library, n, d, op] = statistics.median(values)
        totals = [sum(s['microseconds'] for s in rows if s['round'] == r and s['operation'].startswith('query')) for r in range(5)]
        summary[library, n, d, 'query64'] = statistics.median(totals)
        aggregate.append(dict(library=library, size=n, distribution=d,
                              build_median_us=summary[library, n, d, 'build'],
                              query64_median_us=statistics.median(totals),
                              query64_min_us=min(totals), query64_max_us=max(totals)))
with (primary / 'aggregate.csv').open('w', newline='') as out:
    writer = csv.DictWriter(out, fieldnames=list(aggregate[0]))
    writer.writeheader()
    writer.writerows(aggregate)

query_ratios = [summary['Tedd bulk reused', f['size'], f['distribution'], 'query64'] /
                summary['static_aabb2d_index', f['size'], f['distribution'], 'query64'] for f in fixtures]
static_wins = sum(min(order, key=lambda name: summary[name, f['size'], f['distribution'], 'query64']) ==
                  'static_aabb2d_index' for f in fixtures)
large_build_ratios = [summary['Tedd bulk reused', 100000, d, 'build'] /
                      summary['geo-index Hilbert', 100000, d, 'build'] for d in ('uniform', 'clustered')]

report = ['# Cross-language spatial-index comparison', '',
          'Measured 2026-10-17 against Tedd.RTree commit `9d8fb597932bca550ab7d7092af6b35c5a15a09b`.', '',
          'Eight competing libraries were screened and benchmarked across C, C++, Go, Rust, and JavaScript. '
          'These measurements identify winners for the tested workloads; they do not establish a universal fastest spatial index.', '',
          f'`static_aabb2d_index` had the lowest aggregate query median in {static_wins} of six fixtures. '
          f'Tedd’s bulk-loaded reused-list query time divided by its query time ranged from {min(query_ratios):.2f}× to {max(query_ratios):.2f}×. '
          f'At 100,000 entries, Tedd bulk construction time divided by `geo-index` Hilbert construction time ranged from {min(large_build_ratios):.2f}× to {max(large_build_ratios):.2f}×. '
          'Both competitors are immutable packed indexes. Wide queries dominate the aggregate mix; selective-query rankings differ.', '',
          '## Results across fixture sizes', '',
          'Each cell uses the median of five fresh-process block averages. “Tedd / winner” is the ratio of Tedd bulk/reused time to the fastest measured time; a larger ratio means Tedd took longer. '
          'Aggregate query time is the sum of four separately timed 16-query groups within each process, followed by the median across processes.', '',
          '| Entries | Distribution | Fastest construction | Tedd / winner | Fastest aggregate queries | Tedd / winner |',
          '|---:|---|---|---:|---|---:|']
for f in fixtures:
    n, d = f['size'], f['distribution']
    # Allocating/reused Tedd and the two Boost query APIs share their build algorithm.
    build_candidates = [name for name in order if name not in ('Tedd bulk allocating', 'Boost.Geometry visitor')]
    winner_build = min(build_candidates, key=lambda name: summary[name, n, d, 'build'])
    winner_query = min(order, key=lambda name: summary[name, n, d, 'query64'])
    build_ratio = summary['Tedd bulk reused', n, d, 'build'] / summary[winner_build, n, d, 'build']
    query_ratio = summary['Tedd bulk reused', n, d, 'query64'] / summary[winner_query, n, d, 'query64']
    report.append(f'| {n:,} | {d} | {winner_build} | {build_ratio:.2f}× | {winner_query} | {query_ratio:.2f}× |')

for d in ('uniform', 'clustered'):
    report += ['', f'## 100,000 entries: {d}', '',
               'Construction is milliseconds per new index/lifecycle operation. Query columns are microseconds per 16 queries; lower is faster.', '',
               '| Library/API | Build ms | Point | Width 20 | Width 200 | Width 1,000 | Aggregate 64 µs |',
               '|---|---:|---:|---:|---:|---:|---:|']
    for library in order:
        cells = [f'{summary[library,100000,d,"build"]/1000:.3f}']
        cells += [f'{summary[library,100000,d,op]:.2f}' for op in ('query0','query1','query2','query3','query64')]
        report.append('| ' + library + ' | ' + ' | '.join(cells) + ' |')

report += ['', '## Query result volumes', '',
           'Total matches across each 16-query group, counting an entry again when it matches another query. '
           'Several clustered selective-query groups have no matches; their timings measure rejection/traversal.', '',
           '| Entries | Distribution | Point hits | Width 20 hits | Width 200 hits | Width 1,000 hits |',
           '|---:|---|---:|---:|---:|---:|']
for f in fixtures:
    counts = [sum(f['hits'][g::4]) for g in range(4)]
    report.append('| ' + f'{f["size"]:,} | {f["distribution"]} | ' + ' | '.join(f'{v:,}' for v in counts) + ' |')

report += ['', '## Libraries and execution paths', '',
           '| Library | Construction | Mutation after construction | Query output |',
           '|---|---|---|---|',
           '| Tedd.RTree (.NET) | STR bulk; separate incremental variant | Supported | Reused `List<int>`; separate allocating variant |',
           '| [Tidwall C](https://github.com/tidwall/rtree.c) | Incremental | Supported | Callback into reused ID vector |',
           '| [Tidwall Go](https://github.com/tidwall/rtree) | Incremental | Supported | Generic integer payload; callback into reused ID slice |',
           '| [Superliminal C++](https://github.com/nushoin/RTree) | Incremental | Supported | Callback into reused ID vector |',
           '| [Boost.Geometry](https://www.boost.org/doc/libs/latest/libs/geometry/doc/html/geometry/spatial_indexes/rtree_quickstart.html) | Packed range constructor, `rstar<16>` | Supported | `qbegin`; supplementary `query` output iterator |',
           '| [GeoRust rstar](https://github.com/georust/rstar) | Bulk | Supported | Intersection iterator into reused ID vector |',
           '| [GeoRust geo-index](https://github.com/georust/geo-index) | Hilbert or STR packing | Immutable | Allocating search |',
           '| [static_aabb2d_index](https://github.com/jbuckmccready/static_aabb2d_index) | Hilbert packing | Immutable | Visitor with reused ID vector and traversal stack |',
           '| [Flatbush](https://github.com/mourner/flatbush) | Hilbert packing | Immutable | Allocating search |', '',
           'Node capacities are 16 except Tidwall C/Go (upstream default 64) and `rstar` (upstream default 6). '
           'No node-capacity tuning sweep was performed. Source snapshots are pinned in [sources.lock.json](cross-language/sources.lock.json), '
           'including development snapshots whose manifest versions need not represent published releases.', '',
           '## Source screening before execution', '',
           '- Reviewed indexing entry points, imports, allocation/callback paths, manifests, and dependency build scripts. '
           'The worker execution paths perform in-memory indexing and fixture reads, with no database or network operations.',
           '- C uses ordinary allocation and reference-counted nodes; Go uses documented unsafe node-layout conversions. '
           'Superliminal has optional serialization methods, which the worker never calls. Boost uses header-only index construction/search.',
           '- `rstar` forbids unsafe code in its own crate. `geo-index` uses unchecked slice indexing; reviewed its builder and search bounds. '
           '`static_aabb2d_index` was compiled with its default safe configuration and forbids unsafe code in that configuration.',
           '- Flatbush and its sole runtime dependency FlatQueue contain array/index/queue operations. Dependencies were copied from reviewed sources; npm hooks were not run.',
           '- Rust dependency build scripts perform compiler-capability probes and generate configuration files under the task workspace. '
           'Compiler subprocesses and generated-file paths were inspected before compilation. No upstream benchmark, demonstration, installer, or deployment scripts ran.',
           '- The portable Go archive was verified against the SHA-256 supplied by the official Go download service. '
           'This was a limited source/reputation screening, not a comprehensive security audit.', '',
           '## Measurement conditions and limits', '',
           'AMD Ryzen 9 5950X; Windows 10.0.26200 x64; .NET runtime 10.0.13 / SDK 10.0.402; '
           'Clang 22.1.3; Rust 1.93.1; Go 1.27.2; Node 24.11.1. C/C++ use `-O3 -DNDEBUG -march=native`; '
           'Rust uses release optimization, thin LTO, one codegen unit, and `target-cpu=native`. '
           '.NET tiered compilation is disabled; this differs from the earlier BenchmarkDotNet comparison, which retained default tiering/PGO.', '',
           'Five fresh processes per library/fixture, serial execution, Windows affinity mask `4` (logical CPU 2), '
           '100 ms minimum discarded calibration followed by a block with the same repetition count. '
           'Process/block averages describe throughput, not per-request tail latency. Background activity and power policy were uncontrolled. '
           'Observed ranges are retained in the raw summaries; no formal significance test or cross-machine claim is made.', '',
           'All implementations receive identical integer-valued 2D double-precision rectangles and inclusive-intersection queries. '
           'Fixture generation uses a fixed LCG; the seed, code, fixture hashes, and hit counts are retained. '
           'Result IDs are fully materialized and consumed. Every process verifies exact sorted result IDs against brute force before timing. '
           'The separate four-entry probes exercise duplicate bounds, negative coordinates, zero-area rectangles, edge contact, complete coverage, and no matches.', '',
           'Construction includes required input copies and normal object lifetime/reclamation costs. Native/Rust destruction is synchronous; '
           'managed runtimes reclaim indexes through GC. Geometry preparation and fixture parsing are outside timing. '
           'These are construction/lifecycle costs rather than allocator-independent build times. Immutable indexes have a different contract from mutable trees. '
           'Memory footprint, concurrent access, updates/removals, 3D, noninteger geometry, real-world datasets, and more than 100,000 entries are not measured.', '',
           'Payload and result-buffer representations follow each native API; their element widths and runtime overheads differ. '
           'This compares usable library configurations, not language execution cost in isolation. Compiler flags, node capacities, '
           'and allocation policies are disclosed rather than treated as identical.', '',
           'Boost’s output-iterator API and `static_aabb2d_index` form a supplementary cohort run after the primary cohort with the same fixtures and timing policy. '
           'Their process ranges and cohort identity remain separate. Treat small cross-cohort differences cautiously.', '',
           '## Evidence and reproduction', '',
           '[Harness and instructions](cross-language/REPRODUCE.md); [source/compiler identities](cross-language/sources.lock.json); '
           '[primary samples](results/cross-language/samples.json); [primary operation medians/ranges](results/cross-language/summary.csv); '
           '[supplementary samples](results/cross-language-supplementary/samples.json); '
           '[supplementary operation medians/ranges](results/cross-language-supplementary/summary.csv); '
           '[combined aggregate comparison](results/cross-language/aggregate.csv); '
           '[fixture hashes and hit counts](results/cross-language/fixtures.json).', '',
           'The existing Tedd.RTree differential and boundary test executable passed in Release. '
           'All 390 benchmark processes and 13 boundary-probe processes passed their exact result-set checks '
           '(25,012 query/result-set comparisons). No production implementation changes were made.', '']
# 13 variants * 6 fixtures * 5 processes * 64 queries + 13 probe processes * 4 queries.
assert 13*6*5*64 + 13*4 == 25012
(benchmarks / 'CROSS-LANGUAGE.md').write_text('\n'.join(report), encoding='utf8')
print('Report and aggregate comparison written.')
