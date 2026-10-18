"""Summarize every frozen process and retain ranges, including the previous Tedd reference."""
import csv, json, statistics
from pathlib import Path

root=Path(__file__).resolve().parents[2]
folder=root/'benchmarks/results/csharp-charts'
data=json.loads((folder/'samples.json').read_text())
processes=json.loads((folder/'processes.json').read_text())
protocol=json.loads((folder/'protocol.json').read_text())
assert len(processes)==len(protocol['jobs'])==180
assert all(p['returncode']==0 for p in processes)
rows=[]
for n in (1000,10000,100000):
    for distribution in ('uniform','clustered'):
        fingerprints={p['validation'].split(';expected=')[1].split(';')[0] for p in processes if (p['size'],p['distribution'])==(n,distribution)}
        assert len(fingerprints)==1, 'Different timed useful work'
        for library in ('candidate','rbush','nts-list','nts-visitor','rtree','enyim'):
            subset=[d for d in data if (d['size'],d['distribution'],d['library'])==(n,distribution,library)]
            assert len(subset)==25
            for operation in ('build','query0','query1','query2','query3','queries'):
                groups=['query0','query1','query2','query3'] if operation=='queries' else [operation]
                values=[sum(d['microseconds'] for d in subset if d['round']==r and d['operation'] in groups) for r in range(5)]
                allocation=[sum(d['allocation_bytes'] for d in subset if d['round']==r and d['operation'] in groups) for r in range(5)]
                rows.append(dict(size=n,distribution=distribution,library=library,operation=operation,median_us=statistics.median(values),min_us=min(values),max_us=max(values),median_allocation_bytes=statistics.median(allocation)))
with (folder/'summary.csv').open('w',newline='') as out:
    writer=csv.DictWriter(out,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
previous=list(csv.DictReader((root/'benchmarks/results/mutation-regressions/cross/summary.csv').open()))
reference=[]
for r in rows:
    if r['library']!='candidate' or r['operation'] not in ('build','queries'):continue
    old=next(p for p in previous if (int(p['size']),p['distribution'],p['library'],p['operation'])==(r['size'],r['distribution'],'candidate',r['operation']))
    reference.append(dict(size=r['size'],distribution=r['distribution'],operation=r['operation'],previous_median_us=float(old['median_us']),fresh_median_us=r['median_us'],fresh_over_previous=r['median_us']/float(old['median_us'])))
(folder/'tedd-reference.json').write_text(json.dumps(reference,indent=2))
print('Validated 180 workers and all 64 exact result sets per process; wrote complete medians/ranges/allocation.')
