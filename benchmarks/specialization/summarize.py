"""Render all frozen confirmation/comparison results; never publishes a website."""
import sys
sys.dont_write_bytecode=True
import csv,json
import research as r

def lookup(phase):
    rows=json.loads((r.EVIDENCE/phase/'summary.json').read_text())
    return {(x['size'],x['distribution'],x['mode'],x['operation']):x for x in rows}

def main():
    tables=[]
    for phase in ('confirmation','tiered'):
        data=lookup(phase)
        tables.append(f'## {phase}\n\nMedian microseconds; queries materialize and consume all IDs from 64 windows. Ratios below 1 favor packed.\n\n| Entries | Distribution | Operation | Mutable | Packed | Packed / mutable |\n|---:|---|---|---:|---:|---:|')
        for n in (1000,10000,100000):
            for d in ('uniform','clustered'):
                for op in ('build','queries'):
                    a=data[n,d,'mutable',op]['median_us'];b=data[n,d,'packed',op]['median_us']
                    tables.append(f'| {n:,} | {d} | {op} | {a:.3f} | {b:.3f} | {b/a:.3f} |')
    groups={'packed':('PackedRTree (experimental C#)',['packed']), 'mutable':('Tedd.RTree (C#)',['mutable']),
        'rbush':('RBush (C#)',['rbush']),'nts':('NetTopologySuite (C#)',['nts-list','nts-visitor']),
        'rtree':('RTree (C#)',['rtree']),'enyim':('Enyim.Collections.RTree (C#)',['enyim'])}
    for mode,label in (('static','static_aabb2d_index'),('geo-hilbert','geo-index Hilbert'),('geo-str','geo-index STR')):
        groups[mode]=(label+' (Rust)',['direct-'+mode,'native-'+mode])
    data=lookup('comparison');results=[];ranks=[]
    tables.append('## Fresh complete comparison\n\nLower whole-operation median selects NTS list/visitor or Rust direct/interop; all individual modes remain in raw summaries. Ratios above 1 favor packed. This finite matrix does not establish universal dominance.\n\n| Entries | Distribution | Operation | Packed (us) | Fastest other | Other (us) | Other / packed |\n|---:|---|---|---:|---|---:|---:|')
    for n in (1000,10000,100000):
        for d in ('uniform','clustered'):
            for op in ('build','queries'):
                case=[]
                for library,(label,modes) in groups.items():
                    row=min((data[n,d,m,op] for m in modes),key=lambda x:x['median_us'])
                    result=dict(size=n,distribution=d,operation=op,library=library,label=label,mode=row['mode'],medianUs=row['median_us'],minUs=row['min_us'],maxUs=row['max_us'],allocated=row['allocated'])
                    case.append(result);results.append(result)
                own=next(x for x in case if x['library']=='packed');other=min((x for x in case if x['library']!='packed'),key=lambda x:x['medianUs'])
                external=min((x for x in case if x['library'] not in ('packed','mutable')),key=lambda x:x['medianUs'])
                ratio=other['medianUs']/own['medianUs']
                ranks.append(dict(size=n,distribution=d,operation=op,packed_us=own['medianUs'],best_other=other['library'],other_us=other['medianUs'],speedup=ratio,packed_wins=ratio>1,best_external=external['library'],external_us=external['medianUs'],external_speedup=external['medianUs']/own['medianUs'],beats_external=external['medianUs']>own['medianUs']))
                tables.append(f'| {n:,} | {d} | {op} | {own["medianUs"]:.3f} | {other["label"]} | {other["medianUs"]:.3f} | {ratio:.3f} |')
    tables.append(f'\nPacked wins {sum(x["beats_external"] for x in ranks)}/12 against the seven external competitors, or {sum(x["packed_wins"] for x in ranks)}/12 when the existing mutable tree is also a competing choice. The mutable tree wins both 10k construction cells. This is not an automatically dispatched implementation.\n')
    tables.append('\nAll medians and ranges are descriptive. Desktop load, thermals and frequency are uncontrolled; fresh processes and repetitions do not establish independence, significance or tail latency. Native allocation is unavailable. NTS visitor visits every ID; other selected query APIs materialize IDs. Build/reclamation contracts differ as declared in REPORT.md. Mutation capability is not a zero-cost timing entry. SharpTrees remains unranked after its retained correctness failure.\n')
    (r.REPORT/'RESULTS.md').write_text('# Confirmed specialization results\n\n'+'\n'.join(tables),encoding='utf8',newline='\n')
    (r.REPORT/'comparison-ready.json').write_text(json.dumps(dict(date='2026-10-19',status='experimental proposal; production library unchanged',source_patch_sha256=r.digest(r.REPORT/'specialization.patch'),blocks=3,ranking='lower complete-operation median of declared API/execution modes',results=results),indent=2))
    with (r.REPORT/'comparison.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    (r.REPORT/'rankings.json').write_text(json.dumps(ranks,indent=2))
    print(json.dumps(dict(wins=sum(x['packed_wins'] for x in ranks),external_wins=sum(x['beats_external'] for x in ranks),cases=len(ranks),losses=[x for x in ranks if not x['packed_wins']]),indent=2))

if __name__=='__main__':main()
