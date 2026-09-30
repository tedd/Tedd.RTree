"""Derive the standard report from durable paired samples and BDN iteration logs."""
import collections
import csv
import datetime
import json
import pathlib
import re
import statistics

RUN = pathlib.Path(__file__).resolve().parent
RAW = RUN / 'raw'

def samples(filename):
    grouped = collections.defaultdict(list)
    for row in csv.DictReader((RAW / filename).open()):
        grouped[(row['Scenario'], row['Variant'])].append(float(row['Microseconds']))
    return grouped

def measurement(values):
    return dict(median=statistics.median(values), min=min(values), max=max(values), n=len(values))

def paired_series(title, data, cases, before='Before', after='After'):
    rows = []
    for case in cases:
        a = measurement(data[(case, before)]); b = measurement(data[(case, after)])
        b['changePercent'] = (b['median']/a['median']-1)*100
        rows.append(dict(label=case, measurements=[a,b]))
    return dict(title=title, unit='µs / 64 queries', lowerIsBetter=True,
                description='Bars show medians; whiskers span recorded runs. Compare only within each panel epoch.',
                rounds=['Before','After'], rows=rows)

bdn = collections.defaultdict(list)
active = None
for line in (RAW / 'confirmation-bdn.txt').read_text().splitlines():
    match = re.search(r'// Benchmark: (\w+)\.(\w+):.*\[Shape=(\w+)\]',line)
    if match: active = match.groups()
    match = re.search(r'WorkloadResult\s+\d+:.*?([\d.]+)\s+(ns|us|ms)/op',line)
    if match and active:
        bdn[active].append(float(match[1])*dict(ns=.001,us=1,ms=1000)[match[2]])
(RAW / 'bdn-iterations.json').write_text(json.dumps([dict(suite=s,method=m,shape=q,microseconds=x)
    for (s,m,q),x in bdn.items()],indent=2))

confirm = samples('confirmation-screen.csv')
refine = samples('refinement-screen.csv')
construct = samples('construction-screen.csv')
generic = samples('generic-screen.csv')
follow = samples('followup-screen.csv') if (RAW/'followup-screen.csv').exists() else refine
series = [paired_series('Integrated double-coordinate traversal: paired confirmation',confirm,
    [c for c in sorted({k[0] for k in confirm})])]
bdn_traversal = {(q,m):x for (s,m,q),x in bdn.items() if s=='TraversalBenchmarks'}
series.append(paired_series('Independent BenchmarkDotNet traversal confirmation',bdn_traversal,['Point','Broad','All']))
for family in ['Concurrent','Snapshot']:
    data = {(q,'Before' if m.endswith('Singles') else 'After'): x for (s,m,q),x in bdn.items()
            if s=='BatchBenchmarks' and m.startswith(family)}
    series.append(paired_series(family+' batch: BenchmarkDotNet',data,['Point','Miss']))
series.append(paired_series('Experimental generic transplant (excluded): paired samples',generic,sorted({k[0] for k in generic})))
if (RAW/'generic-repeat-screen.csv').exists():
    repeat = samples('generic-repeat-screen.csv')
    series.append(paired_series('Independent generic repeat',repeat,sorted({k[0] for k in repeat})))
if (RAW/'local-array-screen.csv').exists():
    local = samples('local-array-screen.csv')
    series.append(paired_series('Generic captured-array experiment',local,sorted({k[0] for k in local})))
if (RAW/'generic-final-screen.csv').exists():
    last = samples('generic-final-screen.csv')
    series.append(paired_series('Experimental specialization final acceptance (excluded)',last,sorted({k[0] for k in last})))

cards = []
for row in series[1]['rows']:
    a,b=row['measurements']
    cards.append(dict(title='Double '+row['label'], value=b['median'], unit='µs / 64 queries',
        wallChangePercent=b['changePercent'],baseline=a['median'],secondaryMetric='allocations',
        secondaryChangePercent=0, progression=f"{a['median']:.3f} → {b['median']:.3f}; three BDN iterations each; zero timed allocation"))
for panel in series[2:4]:
    a,b=panel['rows'][0]['measurements']
    cards.append(dict(title=panel['title'].split(':')[0]+' point', value=b['median'],unit='µs / 64 queries',
        wallChangePercent=b['changePercent'],baseline=a['median']))

definitions = [
('Whole-node containment', 'Contains before every recursive traversal','Contained','rejected','Selective overhead; integrated matched-child checks avoid leaf checks.'),
('Root-only containment','Collect entire index only when root is contained','RootContained','rejected','Does not improve partial broad queries; integrated traversal covers full-index queries.'),
('Internal-node containment','Skip checks at leaves','InternalContained','rejected','Broad benefit with inconsistent selective overhead; matched-child combined path preferred.'),
('Bounded active-prefix traversal','One span validation instead of repeated node-array indexing','SpanTraversal','retained','Integrated with matched-child containment; optimized code checked separately.'),
('Cached quadratic seed areas','Precompute each entry area in stack storage','CachedAreas','rejected','No reliable build gain; small uniform build regressed.'),
('Stack-assigned flags','Initialized stack span replacing bool allocation','StackAssigned','rejected','Reduced allocation but construction regressed in screening; not retained.'),
('Linear R-tree splitting','Normalized-separation seeds and one-pass assignment','LinearSplit','rejected','Faster construction; worse medium queries. Default remains quadratic.'),
('Concurrent batch queries','One read lock per batch','ConcurrentBatch','retained','Confirmed query benefit; explicit writer exclusion for the whole batch.'),
('Snapshot batch queries','One published tree captured per batch','SnapshotBatch','retained','Confirmed benefit plus one-version consistency; explicit output ownership.'),
('Existing STR batch construction','Avoid incremental splits with packed construction','STR','not-applicable','Existing public BulkLoad already supplies this algorithm; confirmed construction advantage.'),
('Node capacity sweep','Vary scan width and tree depth','Capacity8','rejected','Smaller capacities improve selective cases and hurt broad cases; default retained.'),
('Flat SIMD index alternative','Replace hierarchy with columnar vector scans','SIMD','rejected','Selective query cost is orders of magnitude higher; no general index replacement justified.'),
('Matched-child containment','Check containment after intersecting internal entries','MatchedContained','rejected','Isolated array version has selective overhead; combined span path confirmed.'),
('Matched-child containment with bounded spans','Combine isolated H-004/H-013 mechanisms','MatchedContainedSpan','retained','Large repeated broad benefit; small-query limits verified independently.'),
('Internal containment with bounded spans','Combine H-003/H-004','InternalContainedSpan','rejected','No compelling advantage over matched-child path.'),
('Point routing','Route zero-width/height queries to original recursive helper','MatchedContainedPoint','rejected','Specialization adds maintenance and did not improve selective results.'),
('Point routing with spans','Combine H-014/H-016','MatchedContainedSpanPoint','rejected','Extra dispatcher and traversal duplication without repeatable advantage.'),
('List-derived leaf counts','Subtract appended list prefix instead of incrementing matches','ListCount','rejected','Focused confirmation found no consistent broad gain and slower selective cases than the integrated control.'),
('Span-bounded value collector','Validate active prefix once in containment collector','SpanCollector','rejected','Full-index throughput improved further, but point queries lost 6–15% versus the integrated control. Selective-query priority excludes this additional tradeoff.'),
('Captured arrays for generic traversal','Hoist entry-array reference and node count; retain safe indexing','LocalArray','rejected','Corrects the 2D-long selective regression, but blanket generic adoption regresses small int/float 2D queries by 8–11% in screening.'),
('Coordinate-specialized generic indexing','Use arrays for 2D long and spans for other coordinates','Specialized','rejected','Long point/small cases passed after specialization. Final generic acceptance remained mixed (several selective cases exceed 5%), so all generic traversal changes were excluded; batch APIs remain.'),
]
hypotheses=[]
for index,(claim,mechanism,variant,state,rationale) in enumerate(definitions,1):
    evidence=['raw/refinement-screen.csv']
    result=rationale
    if 5<=index<=7 or index==10:
        evidence=['raw/construction-screen.csv']
        if variant in ['CachedAreas','StackAssigned','LinearSplit','STR']:
            parts=[]
            for case in sorted({k[0] for k in construct}):
                a=statistics.median(construct[(case,'Quadratic')]);b=statistics.median(construct[(case,variant)])
                parts.append(f'{case}: {a:.2f} → {b:.2f} µs/build ({(b/a-1)*100:.1f}%)')
            result+=' '+'; '.join(parts)
    elif index in [8,9]: evidence=['raw/bdn/results/BatchBenchmarks-report.csv','../../tests/Tedd.RTree.Tests/BatchTests.cs']
    elif index==14: evidence=['raw/confirmation-screen.csv','raw/bdn/results/TraversalBenchmarks-report.csv','raw/generic-screen.csv']; result+=' Retained only in the original 2D double tree. Generic traversal transplants did not pass final regression acceptance.'
    elif index==20: evidence=['raw/local-array-screen.csv']
    elif index==21: evidence=['raw/generic-final-screen.csv','experimental-2D-final.txt','experimental-3D-final.txt']
    elif variant in [v for _,v in follow]:
        parts=[]
        for case in ['Uniform-Point','Uniform-Small','Uniform-Broad','Uniform-All','Clustered-Point','Clustered-Small']:
            if (case,variant) in follow:
                a=statistics.median(follow[(case,'Before')]);b=statistics.median(follow[(case,variant)])
                parts.append(f'{case}: {a:.3f} → {b:.3f} µs/batch ({(b/a-1)*100:.1f}%)')
        result+=' '+'; '.join(parts)
    hypotheses.append(dict(id=f'H-{index:03}',claim=claim,mechanism=mechanism,
        sourceLocation='src/Tedd.RTree/RTree*.cs; concurrent and snapshot wrappers for H-008/H-009',
        observation='Inspected traversal, split, and synchronization paths; broad CPU profile and controlled fixture results.',
        prediction='Repeatable query/build reduction beyond observed dispersion; zero extra timed allocation.',
        falsification='Correctness failure, selective regression above 5%, or no repeatable proportional benefit.',
        change=mechanism,changeScope='moderate' if index in [7,8,9,16,17,21] else 'local',
        maintainability='Additive public API with documented ownership' if index in [8,9] else 'Local traversal change or isolated research-only candidate.',
        codeComments='Adjacent node-prefix and containment invariant comments reference H-004/H-013/H-014.' if state=='retained' and index not in [8,9] else 'API XML documents batch synchronization; rejected candidates remain only in the research rig.',
        result=result,state=state,decision={'retained':'Adopted','rejected':'Rejected','not-applicable':'Existing capability','inconclusive':'Inconclusive'}[state],
        decisionRationale=rationale,evidence=evidence,
        risks=['Uncoordinated host load; local fixture relevance.']+(['Longer writer waits on large concurrent query batches.'] if index==8 else [])))

effects=[]
for case in ['Uniform-Point','Uniform-Broad','Uniform-All']:
    control=measurement(refine[(case,'Before')]); items=[]
    for i in [1,2,3,4,13,14,15,16,17]:
        variant=definitions[i-1][2];candidate=measurement(refine[(case,variant)])
        items.append(dict(hypothesisId=f'H-{i:03}',label=variant,effect=candidate['median']/control['median']-1,
            range=[candidate['min']/control['max']-1,candidate['max']/control['min']-1],note='Nine alternating samples'))
    effects.append(dict(name=case,control=f"Before {control['median']:.3f} µs/64 queries",items=items))

coverage={
 'M1':'Batch reuses caller lists; existing workspace controls bulk scratch; no new allocation in acceptance timing.',
 'M2':'H-005/H-006 stack storage tested, not adopted.',
 'M3':'H-004/H-014/H-019/H-020 active-prefix, span, and captured-array experiments.',
 'M4':'Safe span loop removes relevant range checks; unsafe indexing has no remaining justification.',
 'M5':'Existing flat SIMD alternative tested H-012; node-layout redesign adds mutation/layout burden without measured need.',
 'M6':'No sampled cache-miss or indirect-memory-latency evidence warrants prefetch/pinning; node-capacity sweep H-011.',
 'M7':'Batch passes spans without copying input/output storage; cached areas H-005; no codec/copy kernel.',
 'C1':'H-018 output-count dependency; split area reuse H-005.',
 'C2':'H-001/H-002/H-003/H-013 containment placement; point routing H-016/H-017.',
 'C3':'Existing exact four-lane flat scan H-012; generic tree AoS not a vectorized column layout.',
 'C4':'Existing scan uses bit extraction/TZCNT; no relevant division/codec hot path.',
 'C5':'No stencil or neighborhood update kernel.',
 'S1':'Existing one-word SIMD bitmap alternative H-012; bool split flags H-006.',
 'S2':'Location-map mutation not in measured query hot path; no dictionary lookup in queries.',
 'S3':'No immutable query-key dictionary; concurrent location map must support mutation.',
 'S4':'Prior exact-query cache work remains fixture-dependent; query preparation here is already primitive bounds.',
 'S5':'Arbitrary generic values and duplicate rectangles do not establish compressible ordered result runs.',
 'R1':'No opcode dispatch/reflection in measured query traversal; no dispatch table candidate.',
 'R2':'Readonly geometry and byref entries already present; optimized Search inspected for inlining and bounds checks.',
 'R3':'No runtime configuration lookup in hot search.',
 'T1':'No per-worker shared counters; batches are sequential with caller-owned outputs.',
 'T2':'H-009 one-version snapshot batch; existing ReplaceAll/BulkLoad handle update batches.',
 'T3':'H-008 amortizes existing read lock; do not substitute mutex and remove concurrent readers.',
 'T4':'H-008/H-009 batches remove repeated coordination; parallel execution is not needed for this bounded API and has no supplied host-sharing policy.'}
areas=[dict(name=k,boundary='Library query/build paths and wrappers',evidence=v,catalogue='optimize-code '+k,
            hypothesisIds=[],disposition=v) for k,v in coverage.items()]
profile=json.loads((RAW/'profile-summary.json').read_text())
hotspot=next(x for x in profile['inclusive'] if 'BaselineRTree' in x['name'] and 'Node' in x['name'])

a,b=series[1]['rows'][1]['measurements']
report=dict(title='R-tree traversal, alternative algorithms, and batch queries',generatedAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).isoformat(),
 status='complete',scope='Local .NET 10 library query/build experiments on 10,000 entries; no application workload was supplied. Traversal changes retained only in the original 2D double tree; batch APIs span all coordinate variants.',
 question='Can contained-subtree collection and batched synchronization reduce complete query latency without selective regressions?',
 primaryMetric='µs / 64 queries',summary=dict(baseline=a['median'],final=b['median'],unit='µs / 64 queries',changePercent=b['changePercent'],
 headline=f"Broad double queries: {a['median']:.2f} → {b['median']:.2f} µs per batch. Results are local fixture measurements."),
 scorecards=cards,series=series,effectGroups=effects,hypotheses=hypotheses,areas=areas,
 environment=[dict(label=k,value=v) for k,v in {
 'Revision':'e37bbdca4d3781279a55af911efd40664866524c; baseline initially clean; delivered source and preserved baseline classes define candidates.',
 'Runtime':'.NET 10.0.12 x64 RyuJIT x86-64-v3; SDK 10.0.401; BenchmarkDotNet 0.15.8',
 'CPU':'AMD Ryzen 9 5950X; 16 physical / 32 logical cores',
 'OS':'Windows 11 10.0.26200.9457',
 'Execution':'High-performance power plan; no pinned affinity; default tiering/dynamic PGO; BDN concurrent workstation GC.',
 'Epochs':'Initial screening allocated bound-method delegates; confirmation caches them. Never compare absolute values across those epochs.',
 'Lock':'OS-backed cooperative C:/Users/tedd/.codex/locks/performance-measurement.lock. All restores/builds/tests/traces/timing serialized.',
 'Fixtures':'Seed 73211; capacity 16; 64 point/small/medium/broad/all/miss queries; uniform and clustered geometry.'}.items()],
 hotspots=[dict(name='Baseline recursive Search',location='src/Tedd.RTree/RTree.cs',inclusivePercent=hotspot['percent'],
   evidence='12-second EventPipe sample profile; broad caller. Inclusive samples collapse repeated recursive frames.',limit='Repeated descendant geometry comparisons and active-prefix traversal')],
 retainedChanges=['SearchBatch across all nine mutable/concurrent/snapshot coordinate variants.','Matched-child containment and bounded active-prefix traversal in RTree<T> (original 2D double coordinates). Generic tree traversal remains unchanged.'],
 decisions=['R*-tree overlap-aware splitting/reinsertion is a separate design alternative; no implementation or speed claim tested here.',
 'Linear splitting is a construction/query tradeoff, not adopted as the default.',
 'Flat SIMD scans remain research alternatives; no automatic tree-to-scan switching policy adopted.'],
 correctness=['Original differential/boundary/mutation/concurrency checks passed before and after integration.',
 'Batch tests cover append semantics, duplicates, inclusive contact, null lists, buffer prevalidation, empty input/tree, mutation, count tails, four coordinate types, all nine API variants, and concurrent version coherence.',
 'Every measured tree/scan query validated complete sorted value multisets against an independent linear intersection scan.'],
 generatedCode=[
 dict(hypothesisId='H-004',summary='The Tier 1 search leaf loop uses the validated span length without the baseline per-entry node-array length guard. Checks still remain in inlined collection/output paths.',
      before='Baseline loop reloads the node entry array and performs CMP/JAE against its array length per entry.',
      after='Candidate validates array length against node.Count before traversing the active prefix. Do not interpret the remaining RNGCHKFAIL helper as a surviving check in that span loop.',artifact='raw/tiered-search.txt'),
 dict(hypothesisId='H-014',summary='Containment collection reduces geometric work but increases optimized recursive Search code size from 655 to 1,383 bytes in this diagnostic PGO compilation.',
      before='Baseline Search: 655 bytes; scalar inclusive intersection predicates for descendants.',after='Candidate Search: 1,383 bytes; inlined contained-leaf collection and recursive collection fallback. Code-size and register-pressure costs motivate selective regression coverage.',artifact='raw/tiered-search.txt'),
 dict(hypothesisId='H-021',summary='The rejected long-coordinate specialization folds the type condition in Tier 1; no runtime Type/reflection helper reference appears in its optimized search body.',
      before='Universal generic span version regressed 2D-long point/small timings in two runs.',after='Captured-array specialized loop restored those cases; broader generic acceptance still failed. This code was excluded from the library.',artifact='raw/generic-tiered-search.txt')],
 validityThreats=['No application-level speedup is claimed; build/update/query proportions were unspecified.',
 'Uncoordinated external host activity created substantial run drift. Nine interleaved screening samples and independent BDN runs establish large effects; small differences remain uncertain.',
 'BDN ShortRun has three measured iterations and one launch; report ranges and standard deviations, not overly precise universal estimates.',
 'Generic transplants produced large broad-query gains but mixed selective-query acceptance. They were excluded; experimental source and all positive/negative evidence remain available.',
 'Batch lock savings were measured without competing writers. Larger batches can increase writer wait time.'],
 reproduction=["python C:/Users/tedd/.codex/skills/scientific-method-performance/scripts/run_with_performance_lock.py --cwd D:/SourceCode/Tedd.RTree -- python \"Research/2026-09-30 batch-search-1/measure.py\" confirmation",
 'Invoke followup.py with the same shared-lock wrapper for follow-up screening, diagnostic Tier 1 disassembly, and final tracing.',
 'Replay excluded generic experiments by invoking dotnet run --project Investigation.csproj -c Release -p:ExperimentalGenericTraversal=true -- --generic-screen raw/reproduced-generic-screen.csv under the shared-lock wrapper. Snapshot sources preserve the excluded implementation without changing shipped library files.',
 'python make_report.py; render report-data.json using the skill scripts/render_report.py. All paths are relative to this run directory unless specified.'],
 artifacts=[dict(label='Protocol / adaptive ledger',path='protocol.md'),dict(label='Investigation project',path='Investigation.csproj'),
 dict(label='Raw measurements and traces',path='raw/'),dict(label='BenchmarkDotNet exports',path='raw/bdn/results/'),
 dict(label='Independent tests',path='../../tests/Tedd.RTree.Tests/BatchTests.cs'),
 dict(label='Algorithm references',path='https://donar.umiacs.umd.edu/quadtree/docs/rtree_split_rules.html')])
(RUN/'report-data.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('Prepared report-data.json')
