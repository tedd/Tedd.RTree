"""Controlled, in-memory representation research. No production source writes."""
import csv, ctypes, hashlib, json, os, random, shutil, statistics, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[2]
ROOT=Path('D:/Workspaces/AI/rtree-specialization-20261019')
REPORT=REPO/'Research/2026-10-19-specialization'
EVIDENCE=REPO/'benchmarks/results/specialization'
DOTNET=Path('C:/Program Files/dotnet/dotnet.exe')
ENV=dict(os.environ,TEMP=str(ROOT),TMP=str(ROOT),DOTNET_TieredCompilation='0',DOTNET_CLI_TELEMETRY_OPTOUT='1')

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def worker_source():
    for name in ('RadixWorker.cs','CapacityWorker.cs','GuardWorker.cs'):
        if (ROOT/name).exists():return ROOT/name
    return REPO/'benchmarks/specialization/Worker.cs'
def run(cmd,log,env=None,timeout=240):
    p=subprocess.Popen(list(map(str,cmd)),cwd=ROOT,env=env or ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:out,err=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:p.kill();p.wait();raise
    Path(log).write_text(out+'\nSTDERR:\n'+err,encoding='utf8',newline='\n')
    if p.returncode:raise RuntimeError((cmd,p.returncode,out[-4500:],err[-1500:]))
    return out,err,p.pid

def prepare():
    source=ROOT/'library-source/src/Tedd.RTree';source.mkdir(parents=True,exist_ok=False)
    for p in (REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,source/p.name)
    for name in ('IReadOnlySpatialIndex.cs','PartialOrder.cs','PackedRTree.cs'):shutil.copyfile(REPORT/name,source/name)
    p=source/'RTree.cs';t=p.read_text();t=t.replace('public sealed class RTree<T>','public sealed class RTree<T> : IMutableSpatialIndex<Rectangle, T>',1)
    p.write_text(t,encoding='utf8',newline='\n')
    t=t.replace('public sealed class RTree<T>','public sealed class PartitionRTree<T>',1).replace('public RTree(', 'public PartitionRTree(',1)
    start=t.index('        // Primitive keys');end=t.index('        Node[] level',start)
    t=t[:start]+'''        Span<int> scatter = workspace is null ? new int[itemCount] : workspace.HilbertScatter(itemCount);
        PartialOrder.Sort(keys, order, scatter, _capacity);
'''+t[end:]
    (source/'PartitionRTree.cs').write_text(t,encoding='utf8',newline='\n')
    build()

def build():
    source=ROOT/'library-source/src/Tedd.RTree/Tedd.RTree.csproj'
    run([DOTNET,'build',source,'-c','Release','--artifacts-path',ROOT/'library-artifacts','-o',ROOT/'library','-p:UseSharedCompilation=false'],ROOT/'library-build.txt')
    project=ROOT/'Bench.csproj'
    extra=f'<Compile Include="{REPORT}/ExtraChecks.cs"/>' if (ROOT/'library-source/src/Tedd.RTree/ColumnPackedRTree.cs').exists() else ''
    if (ROOT/'GuardWorker.cs').exists():extra+=f'<Compile Include="{REPORT}/GuardChecks.cs"/>'
    if (ROOT/'RadixWorker.cs').exists():extra+=f'<Compile Include="{REPORT}/RadixChecks.cs"/>'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><AssemblyName>Bench</AssemblyName><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{worker_source()}"/><Compile Include="{REPORT}/ResearchChecks.cs"/>{extra}<Reference Include="Tedd.RTree"><HintPath>{ROOT}/library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''',encoding='utf8')
    # Distinct output epochs prevent stale assembly-reference caches after adding types.
    epoch=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(source.parent.glob('*.cs')))).hexdigest()[:12]
    (ROOT/'caller').mkdir(exist_ok=True)
    # RAR can prefer an existing output copy with the same assembly identity.
    # Both possible resolution locations must contain the new implementation.
    shutil.copyfile(ROOT/'library/Tedd.RTree.dll',ROOT/'caller/Tedd.RTree.dll')
    run([DOTNET,'build',project,'-c','Release','--artifacts-path',ROOT/f'caller-artifacts-{epoch}','-o',ROOT/'caller','-p:UseSharedCompilation=false'],ROOT/f'caller-build-{epoch}.txt')
    shutil.copyfile(ROOT/'library/Tedd.RTree.dll',ROOT/'caller/Tedd.RTree.dll')
    assert digest(ROOT/'library/Tedd.RTree.dll')==digest(ROOT/'caller/Tedd.RTree.dll')

def tests(full=True):
    fixture=ROOT/'retained/fixture-1000-uniform.txt'
    for scalar in (False,True):
        env=dict(ENV)
        if scalar:env['DOTNET_EnableHWIntrinsic']='0'
        run([DOTNET,'exec','--fx-version','10.0.13',ROOT/'caller/Bench.dll',fixture,'flat','validate'],REPORT/f'research-tests-{scalar}.txt',env=env)
    if not full:return
    project=ROOT/'Tests.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{REPO}/tests/Tedd.RTree.Tests/*.cs"/><Reference Include="Tedd.RTree"><HintPath>{ROOT}/library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''',encoding='utf8')
    run([DOTNET,'build',project,'-c','Release','--artifacts-path',ROOT/'test-artifacts','-o',ROOT/'tests','-p:UseSharedCompilation=false'],ROOT/'test-build.txt')
    shutil.copyfile(ROOT/'library/Tedd.RTree.dll',ROOT/'tests/Tedd.RTree.dll')
    for scalar in (False,True):
        env=dict(ENV)
        if scalar:env['DOTNET_EnableHWIntrinsic']='0'
        run([DOTNET,'exec','--fx-version','10.0.13',ROOT/'tests/Tests.dll'],REPORT/f'full-tests-{scalar}.txt',env=env)
    print('Research and existing full suites pass with hardware enabled/disabled.',flush=True)

def summarize(destination):
    samples=json.loads((destination/'samples.json').read_text());result=[]
    keys=sorted({(r['size'],r['distribution'],r['mode']) for r in samples})
    for n,d,m in keys:
        rs=[r for r in samples if (r['size'],r['distribution'],r['mode'])==(n,d,m)]
        for op in sorted({r['operation'] for r in rs}|{'queries','post-queries'}):
            if op in ('queries','post-queries'):
                prefix='query' if op=='queries' else 'mutated'
                if not any(r['operation'].startswith(prefix) for r in rs):continue
                values=[sum(r['us'] for r in rs if r['block']==b and r['operation'].startswith(prefix)) for b in sorted({r['block'] for r in rs})];alloc=None
            else:
                values=[r['us'] for r in rs if r['operation']==op];aa=[r['allocated'] for r in rs if r['operation']==op]
                alloc=statistics.median(aa) if all(v is not None for v in aa) else None
            result.append(dict(size=n,distribution=d,mode=m,operation=op,median_us=statistics.median(values),min_us=min(values),max_us=max(values),allocated=alloc))
    (destination/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    for r in result:
        if r['operation'] in ('build','queries'):print(r,flush=True)

def measure(phase):
    if phase=='exploration':modes,rounds,seed=['mutable','partition','flat','flat-partition'],3,191041
    elif phase=='columns':modes,rounds,seed=['flat','soa-0','soa-128','soa-256'],3,191042
    elif phase=='keys':modes,rounds,seed=['mutable','flat','flat-simd'],3,191043
    elif phase=='guards':modes,rounds,seed=['mutable','partition','guard-mutable','guard-flat'],3,191044
    elif phase=='leaf-columns':modes,rounds,seed=['flat','soa-128','leaf-128','leaf-256'],3,191045
    elif phase=='capacities':modes,rounds,seed=['cap-4','cap-8','cap-16','cap-32'],3,191046
    elif phase=='small-radix':modes,rounds,seed=['flat-simd','small-radix'],3,191047
    else:raise RuntimeError('Unplanned phase')
    jobs=[(b,n,d,m) for b in range(rounds) for n in (1000,10000,100000) for d in ('uniform','clustered') for m in modes]
    random.Random(seed).shuffle(jobs)
    dest=EVIDENCE/phase;dest.mkdir(parents=True,exist_ok=False)
    runtime=Path('C:/Program Files/dotnet/shared/Microsoft.NETCore.App/10.0.13')
    protocol=dict(jobs=jobs,seed=seed,library=digest(ROOT/'caller/Tedd.RTree.dll'),caller=digest(ROOT/'caller/Bench.dll'),
        library_source={p.name:digest(p) for p in (ROOT/'library-source/src/Tedd.RTree').glob('*.cs')},
        caller_source=digest(worker_source()),driver=digest(__file__),runtime='10.0.13',
        runtime_hashes={n:digest(runtime/n) for n in ('coreclr.dll','clrjit.dll','System.Private.CoreLib.dll')},
        affinity=4,tiering=False,observer='none',calibration_us=100000,
        fixtures={f'{n}-{d}':digest(ROOT/f'retained/fixture-{n}-{d}.txt') for n in (1000,10000,100000) for d in ('uniform','clustered')})
    (dest/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf8')
    shutil.copyfile(__file__,dest/'driver.py.txt');samples=[];launches=[]
    for index,(block,n,d,m) in enumerate(jobs):
        cmd=[DOTNET,'exec','--fx-version','10.0.13',ROOT/'caller/Bench.dll',ROOT/f'retained/fixture-{n}-{d}.txt',m]
        started=time.time_ns();out,err,pid=run(cmd,dest/f'{index:03d}.out')
        expected='validated=128' if m in ('mutable','partition','guard-mutable') else 'validated=64'
        if expected not in err:raise RuntimeError('Validation missing')
        launches.append(dict(block=block,size=n,distribution=d,mode=m,pid=pid,started_ns=started,validation=err.strip(),command=list(map(str,cmd))))
        for row in csv.reader(out.splitlines()):
            op,us,reps,allocation=row
            samples.append(dict(block=block,size=n,distribution=d,mode=m,operation=op,us=float(us),repetitions=int(reps),allocated=float(allocation)))
        (dest/'samples.json').write_text(json.dumps(samples,indent=2),encoding='utf8')
        (dest/'launches.json').write_text(json.dumps(launches,indent=2),encoding='utf8')
        print(f'{index+1}/{len(jobs)} {m} {n} {d}',flush=True)
    summarize(dest)

def codegen(prefix='',modes=('mutable','partition','flat','flat-partition')):
    for mode in modes:
        dest=REPORT/f'{prefix}{mode}-jit.txt'
        if dest.exists():raise RuntimeError('Code evidence already exists')
        env=dict(ENV,DOTNET_JitDisasm='*Search* *Sort* *Partition* *.ctor*',DOTNET_JitDisasmAssemblies='Tedd.RTree',DOTNET_JitStdOutFile=str(dest))
        run([DOTNET,'exec','--fx-version','10.0.13',ROOT/'caller/Bench.dll',ROOT/'retained/fixture-10000-uniform.txt',mode,'codegen'],ROOT/f'{mode}-codegen.txt',env=env)

if __name__=='__main__':
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        action=sys.argv[1]
        if action=='prepare':prepare();tests();codegen()
        elif action=='prepare-columns':
            source=ROOT/'library-source/src/Tedd.RTree'
            # Preserve the exact first epoch before a changed-source experiment.
            shutil.copytree(source,ROOT/'epoch1-source')
            shutil.copytree(ROOT/'caller',ROOT/'epoch1-caller')
            import node_layout
            node_layout.generate();node_layout.key_source()
            shutil.copyfile(REPORT/'ColumnPackedRTree.cs',source/'ColumnPackedRTree.cs')
            build();tests();codegen('columns-',('flat','soa-0','soa-128','soa-256','flat-simd'))
        elif action=='build':build();tests()
        elif action=='columns-build':build();tests();codegen('columns-',('flat','soa-0','soa-128','soa-256','flat-simd'))
        elif action=='prepare-guards':
            shutil.copytree(ROOT/'library-source/src/Tedd.RTree',ROOT/'epoch2-source')
            shutil.copytree(ROOT/'caller',ROOT/'epoch2-caller')
            import guard_layout
            guard_layout.generate();build();tests();codegen('guard-',('partition','guard-mutable','guard-flat','leaf-128','leaf-256'))
        elif action=='prepare-capacities':
            shutil.copytree(ROOT/'caller',ROOT/'epoch3-caller')
            t=(ROOT/'GuardWorker.cs').read_text()
            marker='    if (mode == "mutable")'
            t=t.replace(marker,'    if (mode.StartsWith("cap-")) return new KeyPackedRTree<int>(entries, maxEntries: int.Parse(mode[4..]));\n'+marker,1)
            (ROOT/'CapacityWorker.cs').write_text(t,encoding='utf8',newline='\n')
            (REPORT/'capacity-worker.cs.txt').write_text(t,encoding='utf8',newline='\n')
            build();tests(full=False)
        elif action=='prepare-radix':
            shutil.copytree(ROOT/'caller',ROOT/'epoch4-caller')
            source=ROOT/'library-source/src/Tedd.RTree'
            shutil.copytree(source,ROOT/'epoch4-source')
            t=(REPORT/'KeyPackedRTree.cs').read_text().replace('KeyPackedRTree','RadixPackedRTree').replace('Count < 2048','Count < 128')
            (REPORT/'RadixPackedRTree.cs').write_text(t,encoding='utf8',newline='\n')
            (source/'RadixPackedRTree.cs').write_text(t,encoding='utf8',newline='\n')
            t=(ROOT/'CapacityWorker.cs').read_text().replace('    if (mode == "mutable")','    if (mode == "small-radix") return new RadixPackedRTree<int>(entries);\n    if (mode == "mutable")',1)
            t=t.replace('ResearchChecks.Run();','RadixChecks.Run(); ResearchChecks.Run();',1)
            (ROOT/'RadixWorker.cs').write_text(t,encoding='utf8',newline='\n')
            (REPORT/'radix-worker.cs.txt').write_text(t,encoding='utf8',newline='\n')
            build();tests();codegen('radix-',('small-radix',))
        elif action=='codegen':codegen()
        else:measure(action)
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)
