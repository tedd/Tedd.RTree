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
if phase == 'ordering':
    stages, rounds, seed = ('control','hilbert','morton'), 3, 81137
    cases = [(3,t,n,d,'plain') for t,n,d in itertools.product(('int','double'),(10000,100000),('uniform','clustered'))]
elif phase == 'transfer':
    stages, rounds, seed = ('control','candidate'), 3, 31067
    cases = [(2,t,10000,'uniform','plain') for t in types]
elif phase == 'inline':
    stages, rounds, seed = ('algorithm','candidate'), 3, 92731
    cases = [(3,t,100000,d,'plain') for t,d in itertools.product(('int','double'),('uniform','clustered'))] + [(2,t,10000,'uniform','plain') for t in types]
elif phase == 'confirmation':
    stages, rounds, seed = ('control','candidate'), 3, 47381
    cases = [(dim,t,n,d,'plain') for dim,t,n,d in itertools.product((2,3),types,(10000,100000),('uniform','clustered'))]
    cases += [(dim,t,10000,'uniform',m) for dim,t,m in itertools.product((2,3),types,('snapshot','concurrent'))]
else: raise ValueError('Unknown phase')
jobs = [(r,*case,stage) for r,case,stage in itertools.product(range(rounds),cases,stages)]
random.Random(seed).shuffle(jobs)
env = dict(os.environ, DOTNET_TieredCompilation='0')
hashes = {s:{name:hashlib.sha256((root/f'{s}-worker'/name).read_bytes()).hexdigest() for name in ('Bench.dll','Tedd.RTree.dll')} for s in stages}
(output/'protocol.json').write_text(json.dumps(dict(phase=phase,rounds=rounds,shuffle_seed=seed,jobs=jobs,
    hashes=hashes,affinity=4,tiering=False,calibration_ms=100,runtime='10.0.13',observer='no diagnostic capture during timing'),indent=2))
samples, processes = [], []
for i,(block,dim,coordinate,n,distribution,mode,stage) in enumerate(jobs):
    command = ['dotnet','exec','--fx-version','10.0.13',str(root/f'{stage}-worker/Bench.dll'),str(dim),coordinate,str(n),distribution,mode]
    start = time.time_ns()
    p = subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try: stdout,stderr = p.communicate(timeout=240)
    except subprocess.TimeoutExpired: p.kill();p.wait();raise
    if p.returncode or 'validated=' not in stderr: raise RuntimeError((command,stdout,stderr))
    identity = dict(block=block,dimension=dim,coordinate=coordinate,size=n,distribution=distribution,mode=mode,stage=stage)
    processes.append(dict(**identity,pid=p.pid,launch_utc_ns=start,returncode=p.returncode,validation=stderr.strip()))
    for operation,microseconds,iterations,allocation in csv.reader(stdout.splitlines()):
        samples.append(dict(**identity,operation=operation,microseconds=float(microseconds),iterations=int(iterations),allocation_bytes=float(allocation)))
    (output/'samples.json').write_text(json.dumps(samples,indent=2))
    (output/'processes.json').write_text(json.dumps(processes,indent=2))
    print(f'{i+1}/{len(jobs)} {stage} {dim}D {coordinate} {n} {distribution} {mode}',flush=True)
