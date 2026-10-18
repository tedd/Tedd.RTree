"""Derive report tables from complete retained process-block summaries."""
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
RESULTS=REPO/'benchmarks/results/simd'
OUTPUT=REPO/'Research/2026-10-18-simd/RESULTS.md'

def rows(phase): return json.loads((RESULTS/phase/'summary.json').read_text())
def get(data,stage,n,d,op):
    return next(r['median_us'] for r in data if (r['stage'],r['size'],r['distribution'],r['operation'])==(stage,n,d,op))
def change(a,b): return 100*(a/b-1)

text=['# Measured results', '',
      'Production source remains unchanged pending the mutation-scope decision and independent confirmation of the combined SIMD source. Construction parity is supported exploratorily on this Ryzen 5950X/AVX2 host; it is not a release-wide or cross-platform guarantee.', '',
      'All times below are microseconds. Query aggregates sum four measured width groups covering 64 fully materialized and consumed queries. Medians are across complete process blocks; they are descriptive, not confidence intervals or individual latency percentiles. Distinct PIDs do not establish independence. Every observation remains in its original epoch.', '',
      '## Confirmed shared-array layout, scalar key construction', '',
      'Five blocks per fixture. Build, mutation and post-move changes are relative to the matching control. Mutation is one 1,000-move batch per process.', '',
      '| Entries | Distribution | Baseline queries | Shared queries | Query change | Build change | Mutation change | Post-move queries |',
      '|---:|---|---:|---:|---:|---:|---:|---:|']
r=rows('confirmation')
for n in (1000,10000,100000):
    for d in ('uniform','clustered'):
        b=get(r,'baseline',n,d,'aggregate');s=get(r,'selected',n,d,'aggregate')
        ds=[change(get(r,'selected',n,d,op),get(r,'baseline',n,d,op)) for op in ('build','mutation','post-aggregate')]
        text.append(f'| {n:,} | {d} | {b:.3f} | {s:.3f} | {change(s,b):+.1f}% | {ds[0]:+.1f}% | {ds[1]:+.1f}% | {ds[2]:+.1f}% |')
text+=['','Build allocation decreases approximately 2.3–2.4%; mutation allocation increases up to 12.1%. The 12.3% build regression is retained, not erased by later epochs.', '',
       '## SIMD construction alternatives', '',
       'Three blocks per fixture in each distinct study. Ordinary vector source adds eight-lane integer Hilbert/Morton transforms with scalar quantization, tails and fallback. It retains the shared-array layout. Inlining is a separate intervention; it removes the call but does not improve build time against the ordinary vector method.', '',
       '| Study | Distribution | Baseline build | Shared build | Vector build | Inlined build | Vector vs baseline |',
       '|---|---|---:|---:|---:|---:|---:|']
for phase in ('keyvectors','keyinlines'):
    r=rows(phase)
    for d in ('uniform','clustered'):
        b=get(r,'baseline',100000,d,'build');s=get(r,'selected',100000,d,'build');v=get(r,'keyvector',100000,d,'build')
        inline=f'{get(r,"keyinline",100000,d,"build"):.3f}' if phase=='keyinlines' else '—'
        text.append(f'| {phase} | {d} | {b:.3f} | {s:.3f} | {v:.3f} | {inline} | {change(v,b):+.1f}% |')
text+=['','The first vector study narrowly fails its post-move guard (+10.04% uniform). The later four-arm study does not replace that failed observation. Forced inlining is rejected as an unsupported isolated optimization. Both sources require an explicit mutation tradeoff decision and fresh confirmation before adoption. Correctness passes include the full typed/reference suite, scalar dispatch, exact fixture order fingerprints, and a 65,536-tuple scalar/vector key oracle.', '',
       '## Fresh closest-competitor comparison for the scalar shared-array source', '',
       'Three blocks; pinned `static_aabb2d_index` 2.1.0 with native CPU tuning, thin LTO and its unsafe optimizations enabled. Both direct Rust and zero-copy interop are retained; the lower whole-workload median wins. These shared file fixtures differ from the generic-worker fixtures above. They were not rerun for the combined SIMD source.', '',
       '| Entries | Distribution | Shared queries | Best Rust queries | Rust/shared ratio |',
       '|---:|---|---:|---:|---:|']
r=rows('competitors')
for n in (1000,10000,100000):
    for d in ('uniform','clustered'):
        s=get(r,'selected',n,d,'aggregate');v=min(get(r,x,n,d,'aggregate') for x in ('rust-direct','rust-interop'))
        text.append(f'| {n:,} | {d} | {s:.3f} | {v:.3f} | {v/s:.2f}× |')
text+=['','Rust remains faster for 1k uniform; the 10k uniform lead is small. The large-fixture margin is substantial, but no universal ranking follows.', '',
       '## Transfer and runtime guardrails', '',
       'These describe the scalar shared-array source; they are not confirmation of the SIMD combination. Generic/wrapper studies have two blocks and single mutation batches, so large observed changes require cautious interpretation rather than dismissal.', '',
       '| Regime | Query change range | Build change range | Mutation change range | Post-move query range |',
       '|---|---:|---:|---:|---:|']
for phase in ('generic','wrappers','tiered','final-tiered'):
    r=rows(phase);changes={}
    fields=('dimension','coordinate','size','distribution','mode','operation')
    controls={tuple(x[f] for f in fields):x for x in r if x['stage']=='baseline'}
    for x in r:
        if x['stage']!='selected':continue
        b=controls[tuple(x[f] for f in fields)]
        changes.setdefault(x['operation'],[]).append(change(x['median_us'],b['median_us']))
    cells=[]
    for op in ('aggregate','build','mutation','post-aggregate'):
        vals=changes[op];cells.append(f'{min(vals):+.1f}% to {max(vals):+.1f}%')
    text.append('| '+phase+' | '+' | '.join(cells)+' |')
text+=['','`tiered` enables PGO with short calibration only; it is unstable and includes material regressions. `final-tiered` is the separately declared fixed three-second warmup study. Separate normal-exit listings contain Tier1 Search/CollectValues, without proving every timed process had one identical tier state. No startup/first-request claim is made.', '',
       '## Dispositions and limits', '',
       '- Rejected: eager scalar predicates, tested per-rectangle SIMD query predicate, matching-run collection, BMI2 PDEP spreading, fused radix histograms, shared-value chunks, direct leaf fill, count-only span collector, forced vector-helper inlining.',
       '- Shared contiguous values: confirmed original query benefit; documented construction/mutation/transfer tradeoffs, pending adoption decision.',
       '- Eight-lane spatial keys: supported construction remedy, exact code/semantic evidence, pending independent combined-source confirmation and scope decision.',
       '- DotNetLab baseline/shared profiles completed. Latest vector trace completed but stack parsing failed `invalid_path`; the failed operation and unparsed trace are retained. No successful vector reprofile claim.',
       '- No PMU, significance, p99, multicore, Arm/other-CPU performance or hardware-disabled performance claim. Desktop load, frequency/thermal state, short blocks and inter-epoch build variation limit inference.', '',
       'See [REPORT.md](REPORT.md) for prospective protocols, exact IDs, causal limitations, and the full negative-result ledger. Raw process observations, protocols and executable identities are under [benchmarks/results/simd](../../benchmarks/results/simd).', '']
OUTPUT.write_text('\n'.join(text),encoding='utf8',newline='\n')
print(OUTPUT)
