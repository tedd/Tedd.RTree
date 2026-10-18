"""Summarize the predeclared confirmation; retain all process blocks and ranges."""
import csv
import json
from pathlib import Path
import statistics

base = Path(__file__).resolve().parents[1]
folder = base / 'results/mutation-regressions/cross'
data = json.loads((folder / 'samples.json').read_text())
processes = json.loads((folder / 'processes.json').read_text())
assert len(processes) == 240 and all(p['returncode'] == 0 for p in processes)
rows = []
for n in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        for library in sorted({d['library'] for d in data}):
            subset = [d for d in data if (d['size'], d['distribution'], d['library']) == (n, distribution, library)]
            for operation in sorted({d['operation'] for d in subset} | {'queries'} | ({'mutated'} if library in ('control', 'candidate') else set())):
                if operation in ('queries', 'mutated'):
                    prefix = 'query' if operation == 'queries' else 'mutated'
                    values = [sum(d['microseconds'] for d in subset if d['round'] == r and d['operation'].startswith(prefix)) for r in range(5)]
                    allocation = [sum(d['allocation_bytes'] for d in subset if d['round'] == r and d['operation'].startswith(prefix)) for r in range(5)] if library in ('control', 'candidate') else []
                else:
                    selected = [d for d in subset if d['operation'] == operation]
                    assert len(selected) == 5
                    values = [d['microseconds'] for d in selected]
                    allocation = [d['allocation_bytes'] for d in selected if d['allocation_bytes'] is not None]
                rows.append(dict(size=n, distribution=distribution, library=library, operation=operation,
                                 median_us=statistics.median(values), min_us=min(values), max_us=max(values),
                                 median_allocation_bytes=statistics.median(allocation) if allocation else None))
with (folder / 'summary.csv').open('w', newline='') as output:
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)

def value(n, distribution, library, operation, field='median_us'):
    return next(r[field] for r in rows if (r['size'], r['distribution'], r['library'], r['operation']) == (n, distribution, library, operation))

