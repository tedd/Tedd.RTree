"""Prospective A/A and longer-window investigation of every failed primary/supplementary guardrail."""
import csv
import ctypes
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

root=Path(sys.argv[1]).resolve()
assert root==Path('D:/Workspaces/AI/rtree-mutation-regressions').resolve()
repo=Path(__file__).resolve().parents[2]
out=repo/'benchmarks/results/mutation-regressions/final-query-guard';out.mkdir(parents=True,exist_ok=True)
cases=[dict(dimension=2,coordinate='int',size=n,distribution='uniform',mode='plain',move_scale=1,guard_mask=4) for n in (10000,100000)]
stages=('baseline','alias','candidate');rounds=3;seed=43891
jobs=list(itertools.product(range(rounds),range(len(cases)),stages));random.Random(seed).shuffle(jobs)
hashes={s:{n:hashlib.sha256((root/f'{s}-worker'/n).read_bytes()).hexdigest() for n in ('Bench.dll','Tedd.RTree.dll')} for s in stages}
assert len({v['Bench.dll'] for v in hashes.values()})==1
assert hashes['baseline']['Tedd.RTree.dll']==hashes['alias']['Tedd.RTree.dll']
kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=ctypes.c_void_p
kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
assert kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(),4)
protocol=dict(cases=cases,stages=stages,rounds=rounds,seed=seed,jobs=jobs,hashes=hashes,runtime='10.0.13',affinity=4,tiering=False,
    flagged_operation_calibration_ms=1000,other_operation_calibration_ms=100,observer='none',
    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    frozen_production_hashes=json.loads((repo/'benchmarks/results/mutation-regressions/final/protocol.json').read_text())['source_hashes'],
    current_production_hashes={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'src/Tedd.RTree').glob('*.cs')})
(out/'protocol.json').write_text(json.dumps(protocol,indent=2))
samples=[];processes=[]
for i,(block,case_id,stage) in enumerate(jobs):
    c=cases[case_id]
    command=['dotnet','exec','--fx-version','10.0.13',str(root/f'{stage}-worker/Bench.dll'),str(c['dimension']),c['coordinate'],str(c['size']),
        c['distribution'],c['mode'],'guard',str(c['move_scale']),str(c['guard_mask'])]
    start=time.time_ns();p=subprocess.Popen(command,cwd=root,env=dict(os.environ,DOTNET_TieredCompilation='0'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:stdout,stderr=p.communicate(timeout=240)
    except subprocess.TimeoutExpired:p.kill();p.wait();raise
    identity=dict(case_id=case_id,block=block,stage=stage)
    processes.append(dict(**identity,pid=p.pid,launch_utc_ns=start,returncode=p.returncode,validation=stderr.strip()))
    if p.returncode or 'validated=' not in stderr:
        (out/'failure.json').write_text(json.dumps(dict(command=command,stdout=stdout,stderr=stderr,returncode=p.returncode),indent=2));raise RuntimeError('Stability worker failed')
    for operation,microseconds,repetitions,allocation in csv.reader(stdout.splitlines()):
        samples.append(dict(**identity,operation=operation,microseconds=float(microseconds),iterations=int(repetitions),allocation_bytes=float(allocation)))
    (out/'samples.json').write_text(json.dumps(samples,indent=2));(out/'processes.json').write_text(json.dumps(processes,indent=2))
    print(f'{i+1}/{len(jobs)} {stage} case{case_id} {c}',flush=True)
assert len(processes)==18
summary=[]
for case_id,c in enumerate(cases):
    fingerprints={r['validation'].split(';shape=')[1] for r in processes if r['case_id']==case_id}
    assert len(fingerprints)==1,(case_id,'Traversal differs')
    for operation in ('build','queryall','mutation','mutatedall'):
        row=dict(case_id=case_id,**c,operation=operation)
        for stage in stages:
            rs=[r for r in samples if r['case_id']==case_id and r['stage']==stage and r['operation']==operation]
            assert len(rs)==rounds
            values=[r['microseconds'] for r in rs]
            row[stage+'_us']=statistics.median(values);row[stage+'_min_us']=min(values);row[stage+'_max_us']=max(values)
            row[stage+'_allocation']=statistics.median(r['allocation_bytes'] for r in rs)
        row['aa_ratio']=row['alias_us']/row['baseline_us'];row['candidate_ratio']=row['candidate_us']/row['baseline_us']
        row['aa_within_5pct']=0.95<=row['aa_ratio']<=1.05
        row['candidate_within_5pct']=row['candidate_ratio']<=1.05
        row['strict_allocation_guardrail']=row['candidate_allocation']<=row['baseline_allocation']
        summary.append(row)
with (out/'summary.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=summary[0].keys());writer.writeheader();writer.writerows(summary)
for row in summary:
    if not row['aa_within_5pct'] or not row['candidate_within_5pct'] or not row['strict_allocation_guardrail']:print('GUARDRAIL',row,flush=True)
