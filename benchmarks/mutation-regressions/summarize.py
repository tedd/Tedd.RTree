"""Retain every block and report dimension/type/API-specific medians and ranges."""
import csv
import json
from pathlib import Path
import statistics
import sys

base = Path(__file__).resolve().parents[1]
phase = sys.argv[1] if len(sys.argv) > 1 else 'confirmation'
folder = base / 'results/mutation-regressions' / phase
data = json.loads((folder/'samples.json').read_text())
processes = json.loads((folder/'processes.json').read_text())
protocol = json.loads((folder/'protocol.json').read_text())
assert len(processes) == len(protocol['jobs'])
fields = ('dimension','coordinate','size','distribution','mode','stage')
identities = sorted({tuple(d[k] for k in fields) for d in data})
rows = []
for key in identities:
    subset = [d for d in data if tuple(d[k] for k in fields) == key]
    operations = {d['operation'] for d in subset} | {'queries'}
    if any(d['operation'].startswith('mutated') for d in subset): operations.add('mutated')
    for operation in sorted(operations):
        if operation in ('queries','mutated'):
            prefix = 'query' if operation == 'queries' else 'mutated'
            values = [sum(d['microseconds'] for d in subset if d['block']==block and d['operation'].startswith(prefix)) for block in range(3)]
            allocations = [sum(d['allocation_bytes'] for d in subset if d['block']==block and d['operation'].startswith(prefix)) for block in range(3)]
        else:
            observations = [d for d in subset if d['operation']==operation]
            assert len(observations)==3
            values, allocations = [d['microseconds'] for d in observations], [d['allocation_bytes'] for d in observations]
        rows.append(dict(zip(fields,key),operation=operation,median_us=statistics.median(values),min_us=min(values),max_us=max(values),
                         allocation_bytes=statistics.median(allocations)))
with (folder/'summary.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
