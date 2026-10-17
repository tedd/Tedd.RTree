"""Generate exact fixtures and run already-built, inspected workers serially.

Usage: python run.py D:\\Workspaces\\AI\\rtree-cross-language RESULTS_DIRECTORY
No download, build, database, or network operations occur in this runner.
"""
import csv
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

root = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
if not root.is_relative_to(Path('D:/Workspaces/AI').resolve()):
    raise SystemExit('Scratch must be under D:/Workspaces/AI')
destination.mkdir(parents=True, exist_ok=True)
fixtures = []
for n in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        state = 73211
        def next_int(limit):
            global state
            state = (1664525 * state + 1013904223) & 0xffffffff
            return (state >> 8) % limit
        bounds = []
        for i in range(n):
            x = (i % 8) * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            y = (i % 8) * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            bounds.append((x,y,x+next_int(5)+1,y+next_int(5)+1))
        queries = []
        for i in range(64):
            x,y=next_int(1000),next_int(1000)
            width=(0,20,200,1000)[i%4]
            queries.append((x,y,x+width,y+width))
        # Additional correctness probes: duplicate bounds, edge contact, negative coordinates,
        # and complete/outside coverage. These have their own validation-only fixture below.
        path=root/f'{n}-{distribution}.txt'
        data=str(n)+'\n'+'\n'.join(' '.join(map(str,b)) for b in bounds+queries)+'\n'
        path.write_text(data,encoding='ascii')
        hits=[sum(b[0]<=q[2] and b[2]>=q[0] and b[1]<=q[3] and b[3]>=q[1] for b in bounds) for q in queries]
        fixtures.append(dict(size=n,distribution=distribution,path=str(path),sha256=hashlib.sha256(data.encode()).hexdigest(),hits=hits))

workers = {
    'Tedd bulk reused': ['dotnet',str(root/'dotnet/Worker.dll'),'{fixture}','tedd-reuse'],
    'Tedd bulk allocating': ['dotnet',str(root/'dotnet/Worker.dll'),'{fixture}','tedd-alloc'],
    'Tedd incremental': ['dotnet',str(root/'dotnet/Worker.dll'),'{fixture}','tedd-insert'],
    'Tidwall C': [str(root/'tidwall.exe'),'{fixture}'],
    'Superliminal C++': [str(root/'superliminal.exe'),'{fixture}'],
    'Boost.Geometry packed': [str(root/'boost.exe'),'{fixture}'],
    'Tidwall Go': [str(root/'go-worker.exe'),'{fixture}'],
    'rstar bulk': [str(root/'rust/target/release/spatial-comparison.exe'),'{fixture}','rstar'],
    'geo-index Hilbert': [str(root/'rust/target/release/spatial-comparison.exe'),'{fixture}','geo-hilbert'],
    'geo-index STR': [str(root/'rust/target/release/spatial-comparison.exe'),'{fixture}','geo-str'],
    'Flatbush': ['node',str(root/'worker.mjs'),'{fixture}'],
}
if len(sys.argv)>3:
    if sys.argv[3] != 'supplementary':
        raise SystemExit('Unknown supplementary worker')
    workers={
        'Boost.Geometry visitor':[str(root/'boost-query.exe'),'{fixture}'],
        'static_aabb2d_index':[str(root/'static-rust/target/release/static-spatial-comparison.exe'),'{fixture}'],
    }
env=dict(os.environ,DOTNET_TieredCompilation='0',GOMAXPROCS='1')
# Windows child processes inherit this mask. Avoid migration between logical CPUs.
if os.name == 'nt':
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(),4):
        raise ctypes.WinError(ctypes.get_last_error())
def execute(name,fixture):
    command=[x.replace('{fixture}',fixture) for x in workers[name]]
    result=subprocess.run(command,capture_output=True,text=True,env=env,cwd=root,timeout=180)
    if result.returncode or 'validated=' not in result.stderr:
        raise RuntimeError((name,command,result.stdout,result.stderr))
    return result

edge=root/'edges.txt'
edge.write_text('4\n-5 -5 0 0\n-5 -5 0 0\n0 0 0 0\n1 1 2 2\n0 0 0 0\n-6 -6 -5 -5\n-100 -100 100 100\n10 10 20 20\n',encoding='ascii')
for name in workers:
    execute(name,str(edge))
    print(f'Correctness probes passed: {name}',flush=True)
samples=[]
jobs=[(round_number,fixture,name) for round_number in range(5) for fixture in fixtures for name in workers]
random.Random(91823).shuffle(jobs)
started=time.time()
for index,(round_number,fixture,name) in enumerate(jobs):
    result=execute(name,fixture['path'])
    for row in csv.reader(result.stdout.splitlines()):
        if len(row)!=3 or row[0] not in ('build','query0','query1','query2','query3'):
            raise RuntimeError(('Unexpected worker output',name,row))
        samples.append(dict(library=name,size=fixture['size'],distribution=fixture['distribution'],round=round_number,operation=row[0],microseconds=float(row[1]),iterations=int(row[2])))
    (destination/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    print(f'{index+1}/{len(jobs)} {name} {fixture["size"]} {fixture["distribution"]}; {time.time()-started:.0f}s',flush=True)
summary=[]
keys=sorted({(s['library'],s['size'],s['distribution'],s['operation']) for s in samples})
for library,size,distribution,operation in keys:
    values=[s['microseconds'] for s in samples if (s['library'],s['size'],s['distribution'],s['operation'])==(library,size,distribution,operation)]
    summary.append(dict(library=library,size=size,distribution=distribution,operation=operation,median_us=statistics.median(values),min_us=min(values),max_us=max(values),processes=len(values)))
with (destination/'summary.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
(destination/'fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
(destination/'protocol.json').write_text(json.dumps(dict(rounds=5,calibration_ms=100,query_group_size=16,query_widths=[0,20,200,1000],seed=73211,job_shuffle_seed=91823,windows_affinity_mask=4,workers=workers,environment_overrides={'DOTNET_TieredCompilation':'0','GOMAXPROCS':'1'},elapsed_seconds=time.time()-started),indent=2)+'\n')
