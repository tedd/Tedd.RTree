"""Audit complete budgets, deterministic traversal equivalence and prespecified guardrails."""
import csv
import json
from pathlib import Path
import sys

folder = Path(__file__).resolve().parents[1] / 'results/mutation-regressions' / sys.argv[1]
protocol = json.loads((folder/'protocol.json').read_text())
processes = json.loads((folder/'processes.json').read_text())
assert len(processes) == len(protocol['jobs']), 'Incomplete budget'
rows = list(csv.DictReader((folder/'summary.csv').open()))
fields = ('dimension','coordinate','size','distribution','mode')
keys = sorted({tuple(r[k] for k in fields) for r in rows})
report = []
control = 'metrics' if sys.argv[1] == 'integer' else 'mutation' if sys.argv[1] == 'union-inline' else 'baseline'
for key in keys:
    matching = [p for p in processes if tuple(str(p[k]) for k in fields) == key and p['stage'] in (control,'candidate')]
    fingerprints = {p['validation'].split(';shape=')[1] for p in matching}
    assert len(matching) == 6 and len(fingerprints) == 1, (key, 'Traversal differs')
    for operation in (('build','queries') if key[-1] == 'snapshot' else ('build','queries','mutation','mutated')):
        arms = {stage: next(r for r in rows if tuple(r[k] for k in fields) == key and r['stage']==stage and r['operation']==operation)
                for stage in (control,'candidate')}
        before, after = float(arms[control]['median_us']), float(arms['candidate']['median_us'])
        allocation_before, allocation_after = float(arms[control]['allocation_bytes']), float(arms['candidate']['allocation_bytes'])
        report.append(dict(zip(fields,key),operation=operation,baseline_us=before,candidate_us=after,
                           ratio=after/before,allocation_before=allocation_before,allocation_after=allocation_after,
                           time_guardrail=after <= before * 1.05,allocation_guardrail=allocation_after <= allocation_before))
with (folder/'guardrails.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=report[0].keys());writer.writeheader();writer.writerows(report)
print('Validated workers:',len(processes),'cases:',len(keys),'identical traversal fingerprints in every matched case')
for operation in ('mutation','build','queries','mutated'):
    selected = [r for r in report if r['operation']==operation]
    print(operation,'ratio range',min(r['ratio'] for r in selected),max(r['ratio'] for r in selected))
    for r in selected:
        if not r['time_guardrail'] or not r['allocation_guardrail']: print('GUARDRAIL',r)
