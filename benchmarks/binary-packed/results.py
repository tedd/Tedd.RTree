"""Export complete per-library cells; no historical/new timing splicing."""
import sys
sys.dont_write_bytecode=True
import csv,io,json
import study as r

LIBRARIES={
    'mutable':('tedd-rtree','Tedd.RTree mutable (C#)'), 'packed':('tedd-packed','PackedRTree read-only (C#)'),
    'rbush':('rbush','RBush (C#)'), 'nts-list':('nts','NetTopologySuite (C#)'), 'nts-visitor':('nts','NetTopologySuite (C#)'),
    'rtree':('rtree','RTree (C#)'), 'enyim':('enyim','Enyim (C#)'),
    'direct-static':('static','static_aabb2d_index (Rust)'), 'native-static':('static','static_aabb2d_index (Rust)'),
    'direct-geo-hilbert':('geo-hilbert','geo-index Hilbert (Rust)'), 'native-geo-hilbert':('geo-hilbert','geo-index Hilbert (Rust)'),
    'direct-geo-str':('geo-str','geo-index STR (Rust)'), 'native-geo-str':('geo-str','geo-index STR (Rust)')}

def main():
    summaries=json.loads((r.EVIDENCE/'comparison/summary.json').read_text());cells={}
    for value in summaries:
        if value['operation'] not in ('build','queries'):continue
        library,name=LIBRARIES[value['mode']];key=(value['size'],value['distribution'],value['operation'],library)
        row=dict(value,library=library,name=name)
        if key not in cells or value['median_us']<cells[key]['median_us']:cells[key]=row
    assert len(cells)==108
    rankings=[];external_wins=overall_wins=portfolio_wins=0
    for n in (1000,10000,100000):
        for d in ('uniform','clustered'):
            for op in ('build','queries'):
                subset=[v for (nn,dd,oo,_),v in cells.items() if (nn,dd,oo)==(n,d,op)]
                external=min((v for v in subset if v['library'] not in ('tedd-rtree','tedd-packed')),key=lambda v:v['median_us'])
                other=min((v for v in subset if v['library']!='tedd-packed'),key=lambda v:v['median_us'])
                packed=cells[n,d,op,'tedd-packed'];mutable=cells[n,d,op,'tedd-rtree']
                external_wins+=packed['median_us']<external['median_us'];overall_wins+=packed['median_us']<other['median_us']
                portfolio_wins+=min(packed['median_us'],mutable['median_us'])<external['median_us']
                winner=min(subset,key=lambda v:v['median_us'])
                rankings.append(dict(size=n,distribution=d,operation=op,winner=winner,packed=packed,nearest_external=external,nearest_other=other,
                    external_over_packed=external['median_us']/packed['median_us']))
    gates=json.loads((r.REPORT/'adoption-gates.json').read_text())
    data=dict(status='validated isolated proposal; main source application awaits explicit authorization' if gates['passed'] else 'experimental-guard-failure',
        scope='Single CPU, capacity 16, CoreCLR 10.0.13, SDK 10.0.402, tiering disabled, materialized-and-consumed queries; NTS visitor is nonmaterializing.',
        metric='Median microseconds for complete construction or 64 query windows; descriptive, not significance/individual latency.',
        selection='Lower whole-operation mode median for NTS and direct/interop Rust; no group-level or observation minima.',
        source_manifest_sha256=r.sha(r.REPORT/'final-selection.json'),integration_branch='main',published=False,
        packed_wins_external=external_wins,packed_wins_including_mutable=overall_wins,explicit_portfolio_wins_external=portfolio_wins,
        cells=list(cells.values()),rankings=rankings,
        caveats=['No automatic best-of-library dispatch.','Native allocation unavailable; native build includes destruction.','Desktop load/frequency/thermals uncontrolled.','Finite matrix, no all-hardware claim.','SharpTrees remains unranked after its retained correctness failure.'])
    r.atomic_json(r.REPORT/'comparison-ready.json',data);r.atomic_json(r.REPORT/'rankings.json',rankings)
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=['size','distribution','operation','library','name','mode','median_us','min_us','max_us','allocated'])
    writer.writeheader();writer.writerows({k:v[k] for k in writer.fieldnames} for v in cells.values());r.atomic_text(r.REPORT/'comparison.csv',buffer.getvalue())
    lines=['# Confirmed optimization results\n\n','Median microseconds. Queries append and consume all IDs from 64 windows. Complete mode medians select NTS list/visitor and Rust direct/interop; all individual modes remain in raw results. NTS visitor does not materialize IDs.\n\n',
        f'Packed wins {external_wins}/12 against the seven external libraries and {overall_wins}/12 when the existing mutable tree is also a choice. An explicitly best-of-Tedd portfolio wins {portfolio_wins}/12 external cells; it is not an automatically dispatched object.\n\n',
        '| Entries | Distribution | Operation | Packed (us) | Closest external | External (us) | External / packed |\n','|---:|---|---|---:|---|---:|---:|\n']
    for v in rankings:
        a=v['packed'];b=v['nearest_external'];lines.append(f"| {v['size']:,} | {v['distribution']} | {v['operation']} | {a['median_us']:.3f} | {b['name']} | {b['median_us']:.3f} | {v['external_over_packed']:.3f} |\n")
    suffix=json.loads((r.REPORT/'final-selection.json').read_text()).get('confirmation_suffix','-2')
    for phase in ('confirmation'+suffix,'tiered'+suffix,'fallback'+suffix):
        rows=json.loads((r.EVIDENCE/phase/'summary.json').read_text())
        lines.extend(['\n## '+phase+'\n\n','| Entries | Distribution | Mode | Build (us) | Queries (us) |\n','|---:|---|---|---:|---:|\n'])
        table={(v['size'],v['distribution'],v['mode'],v['operation']):v['median_us'] for v in rows}
        for n,d,m in sorted({(v['size'],v['distribution'],v['mode']) for v in rows}):
            lines.append(f'| {n:,} | {d} | {m} | {table[n,d,m,"build"]:.3f} | {table[n,d,m,"queries"]:.3f} |\n')
    lines.append('\nAll original failures, outliers, regime guards and prototype results remain in REPORT.md and raw epoch directories. Process repetitions do not establish independence, significance, p99, or universal dominance. Source integration does not publish NuGet packages or the website.\n')
    r.atomic_text(r.REPORT/'RESULTS.md',''.join(lines))
    print('Complete cells',len(cells),'packed external/overall/portfolio wins',external_wins,overall_wins,portfolio_wins)

if __name__=='__main__':main()
