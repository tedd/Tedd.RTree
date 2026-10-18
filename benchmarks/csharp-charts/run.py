"""Fresh C# supplement to the pinned cross-language fixture; all observations retained."""
import csv, ctypes, hashlib, json, os, random, subprocess, sys, time
from pathlib import Path

root, destination = map(lambda p: Path(p).resolve(), sys.argv[1:])
assert root == Path('D:/Workspaces/AI/rtree-csharp-charts').resolve()
destination.mkdir(parents=True, exist_ok=True)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
assert kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 4)
fixtures = []
for n in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        state = 73211
        def next_int(limit):
            global state
            state = (state * 1664525 + 1013904223) & 0xffffffff
            return (state >> 8) % limit
        boxes = []
        for i in range(n):
            x = i % 8 * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            y = i % 8 * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            boxes.append((x, y, x + next_int(5) + 1, y + next_int(5) + 1))
        queries = []
        for i in range(64):
            x, y = next_int(1000), next_int(1000)
            width = (0, 20, 200, 1000)[i % 4]
            queries.append((x, y, x + width, y + width))
        fixture = root / f'{n}-{distribution}.txt'
        fixture.write_text(str(n) + '\n' + '\n'.join(' '.join(map(str, b)) for b in boxes + queries) + '\n', encoding='ascii')
        fixtures.append((n, distribution, str(fixture)))
names = ['candidate','rbush','nts-list','nts-visitor','rtree','enyim']
jobs = [(r,n,d,f,name) for r in range(5) for n,d,f in fixtures for name in names]
random.Random(49217).shuffle(jobs)
env = dict(os.environ, DOTNET_TieredCompilation='0')
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'worker').glob('*.dll')}
repository = Path(__file__).resolve().parents[2]
protocol = dict(rounds=5,shuffle_seed=49217,jobs=jobs,hashes=hashes,affinity_mask=4,runtime='10.0.13',
    source_revision=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip(),
    source_hashes={str(p.relative_to(repository)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repository/'src/Tedd.RTree').glob('*') if p.is_file()},
    caller_sha256=hashlib.sha256(Path(__file__).with_name('Worker.cs').read_bytes()).hexdigest(),
    fixture_hashes={f'{n}/{d}':hashlib.sha256(Path(f).read_bytes()).hexdigest() for n,d,f in fixtures},
    tiering=False,minimum_calibration_ms=100,observer='none',rust_record='mutation-regressions/cross',
    selection='NTS lower whole-workload median of list/visitor; Rust prior lower direct/interop median; no sample selection')
(destination/'protocol.json').write_text(json.dumps(protocol,indent=2))
# Check boundary semantics in every mode before any timings. The worker does not write databases or start applications.
boundary = root/'boundary.txt'
boundary_results=[]
for boxes in ([],[(-10,-5,0,5),(0,5,10,15),(0,5,10,15),(20,30,21,31)]):
    for reverse in (False,True):
        queries=[(0,5,0,5),(-100,-100,100,100),(100,100,101,101),(21,31,21,31)]
        values=list(reversed(boxes)) if reverse else boxes
        boundary.write_text(str(len(values))+'\n'+'\n'.join(' '.join(map(str,b)) for b in values+queries)+'\n')
        for name in names:
            p=subprocess.run(['dotnet','exec','--fx-version','10.0.13',str(root/'worker/Bench.dll'),str(boundary),name,'validate'],env=env,capture_output=True,text=True)
            boundary_results.append(dict(library=name,size=len(values),reverse=reverse,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
            (destination/'boundaries.json').write_text(json.dumps(boundary_results,indent=2))
            assert p.returncode==0 and 'validated=' in p.stderr,(name,p.stdout,p.stderr)
samples,processes=[],[]
for index,(round_number,n,distribution,fixture,name) in enumerate(jobs):
    command=['dotnet','exec','--fx-version','10.0.13',str(root/'worker/Bench.dll'),fixture,name]
    started=time.time_ns()
    p=subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try: stdout,stderr=p.communicate(timeout=180)
    except subprocess.TimeoutExpired: p.kill(); p.wait(); raise
    record=dict(library=name,size=n,distribution=distribution,round=round_number,pid=p.pid,launch_utc_ns=started,returncode=p.returncode,validation=stderr.strip())
    if p.returncode or 'validated=64;' not in stderr:
        (destination/'failure.json').write_text(json.dumps(dict(**record,stdout=stdout),indent=2));raise RuntimeError('Worker failed')
    processes.append(record)
    for row in csv.reader(stdout.splitlines()):
        operation,us,iterations,allocation=row
        samples.append(dict(library=name,size=n,distribution=distribution,round=round_number,operation=operation,microseconds=float(us),iterations=int(iterations),allocation_bytes=float(allocation)))
    (destination/'processes.json').write_text(json.dumps(processes,indent=2))
    (destination/'samples.json').write_text(json.dumps(samples,indent=2))
    print(f'{index+1}/{len(jobs)} {name} {n} {distribution}',flush=True)
