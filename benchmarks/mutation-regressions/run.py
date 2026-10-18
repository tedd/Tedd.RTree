import csv
import ctypes
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

root, output, phase = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
if not root.is_relative_to(Path('D:/Workspaces/AI').resolve()): raise ValueError('Invalid workspace')
output.mkdir(parents=True, exist_ok=True)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 4): raise ctypes.WinError(ctypes.get_last_error())
types = ('int','long','float','double')
if phase in ('exploration','exploration-metrics','exploration-metrics-matched'):
    stages, rounds, seed = ('baseline','candidate'), 3, (18419 if phase == 'exploration' else 28421)
    cases = [(dim,t,n,d,'plain') for dim,t,(n,d) in itertools.product((2,3),('int','double'),((10000,'clustered'),(100000,'uniform')))]
    cases += [(2,'float',100000,'uniform','plain')]
elif phase in ('confirmation','final'):
    stages, rounds, seed = (('old','baseline','candidate') if phase=='confirmation' else ('baseline','candidate')), 3, (81793 if phase=='confirmation' else 71933)
    cases = [(dim,t,n,d,'plain') for dim,t,n,d in itertools.product((2,3),types,(10000,100000),('uniform','clustered'))]
    cases += [(dim,t,10000,'uniform',m) for dim,t,m in itertools.product((2,3),types,('snapshot','concurrent'))]
elif phase == 'union-inline':
    stages, rounds, seed = ('mutation','candidate'), 3, 31847
    cases = [(2,'double',10000,'uniform','plain'),(2,'double',100000,'uniform','plain'),(2,'long',100000,'uniform','plain'),
        (3,'double',10000,'clustered','plain'),(3,'double',100000,'uniform','plain'),(3,'float',100000,'uniform','plain'),
        (3,'int',100000,'clustered','plain'),(2,'double',100000,'uniform','original'),(3,'long',10000,'uniform','concurrent')]
elif phase == 'integer':
    stages, rounds, seed = ('metrics','candidate'), 3, 57311
    cases = [(dim,t,n,d,'plain') for dim,t,(n,d) in itertools.product((2,3),('int','long'),((10000,'clustered'),(100000,'uniform')))]
elif phase == 'adverse':
    stages, rounds, seed = ('baseline','candidate'), 3, 62713
    cases = [(2,'double',n,d,'original') for n,d in itertools.product((10000,100000),('uniform','clustered'))]
    cases += [(dim,t,10000,'clustered','plain') for dim,t in itertools.product((2,3),('int','double'))]
else: raise ValueError('Unknown phase')
jobs = [(r,*case,stage) for r,case,stage in itertools.product(range(rounds),cases,stages)]
random.Random(seed).shuffle(jobs)
env = dict(os.environ, DOTNET_TieredCompilation='0')
hashes = {s:{name:hashlib.sha256((root/f'{s}-worker'/name).read_bytes()).hexdigest() for name in ('Bench.dll','Tedd.RTree.dll')} for s in stages}
if phase in ('exploration-metrics-matched','confirmation','adverse','integer','union-inline','final'):
    assert len({v['Bench.dll'] for v in hashes.values()}) == 1, 'Caller drift'
repository = Path(__file__).resolve().parents[2]
source_revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repository,text=True).strip()
source_hashes = {str(p.relative_to(repository)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repository/'src/Tedd.RTree').glob('*')) if p.suffix in ('.cs','.csproj')}
(output/'protocol.json').write_text(json.dumps(dict(phase=phase,rounds=rounds,shuffle_seed=seed,jobs=jobs,
    hashes=hashes,source_revision=source_revision,source_hashes=source_hashes,affinity=4,tiering=False,calibration_ms=100,runtime='10.0.13',observer='no diagnostic capture during timing'),indent=2))
samples, processes = [], []
for i,(block,dim,coordinate,n,distribution,mode,stage) in enumerate(jobs):
    command = ['dotnet','exec','--fx-version','10.0.13',str(root/f'{stage}-worker/Bench.dll'),str(dim),coordinate,str(n),distribution,mode,'measure',str(1000 if phase == 'adverse' and mode == 'plain' else 1)]
    start = time.time_ns()
    p = subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try: stdout,stderr = p.communicate(timeout=240)
    except subprocess.TimeoutExpired: p.kill();p.wait();raise
    if p.returncode or 'validated=' not in stderr:
        (output/'failure.json').write_text(json.dumps(dict(command=command,stdout=stdout,stderr=stderr,returncode=p.returncode),indent=2)); raise RuntimeError('Worker failed; evidence retained')
    identity = dict(block=block,dimension=dim,coordinate=coordinate,size=n,distribution=distribution,mode=mode,stage=stage)
    processes.append(dict(**identity,pid=p.pid,launch_utc_ns=start,returncode=p.returncode,validation=stderr.strip()))
    for operation,microseconds,iterations,allocation in csv.reader(stdout.splitlines()):
        samples.append(dict(**identity,operation=operation,microseconds=float(microseconds),iterations=int(iterations),allocation_bytes=float(allocation)))
    (output/'samples.json').write_text(json.dumps(samples,indent=2))
    (output/'processes.json').write_text(json.dumps(processes,indent=2))
    print(f'{i+1}/{len(jobs)} {stage} {dim}D {coordinate} {n} {distribution} {mode}',flush=True)
