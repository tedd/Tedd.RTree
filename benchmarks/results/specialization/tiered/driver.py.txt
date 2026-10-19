"""Frozen specialization confirmation and complete retained-library comparison."""
import sys
sys.dont_write_bytecode=True
import csv,ctypes,json,random,shutil,time
from pathlib import Path
import research as r

def prepare_comparison():
    text=(r.REPO/'benchmarks/csharp-charts/Worker.cs').read_text()
    marker='var index = Indexes.Prepare(args[1], boxes, queries);'
    text=text.replace(marker,'if (args[1].StartsWith("native-")) { NativeBench.Run(boxes, queries, args[1]); return; }\n'+marker)
    start=text.index('            case "candidate":');end=text.index('            case "rbush":',start)
    text=text[:start]+'''            case "mutable":
            case "packed":
                var entries = boxes.Select((b, i) => new SpatialEntry<int>(b, i)).ToArray();
                var result = new List<int>(boxes.Length);
                return new Prepared<IReadOnlySpatialIndex<Rectangle,int>, Rectangle>(() => {
                    if(mode=="packed") return new PackedRTree<int>(entries);
                    var t = new Tedd.RTree.RTree<int>(16); t.BulkLoad(entries); return t;
                }, queries, (t, q) => { result.Clear(); t.Search(q, result); long sum = 0; foreach (int id in result) sum += id + 1; return sum; },
                    (t, q) => t.Search(q));
'''+text[end:]
    (r.ROOT/'ComparisonWorker.cs').write_text(text,encoding='utf8',newline='\n')
    libs=r.ROOT/'comparison-libraries';libs.mkdir(exist_ok=True)
    cache=Path('C:/Users/tedd/.nuget/packages')
    packages=[('rbush','4.0.0','lib/net8.0/RBush.dll'),('nettopologysuite','2.6.0','lib/netstandard2.1/NetTopologySuite.dll'),('rtree','1.1.0','lib/netstandard2.0/RTree.dll'),('enyim.collections.rtree','1.0.5','lib/net45/Enyim.Collections.RTree.dll')]
    records=[];refs=[]
    for name,version,file in packages:
        base=cache/name/version;path=base/file
        # Installed packages are inspected: no executable build hooks. Reference distributed DLLs.
        assert not any(p.suffix.lower() in ('.targets','.props','.exe','.ps1') for p in base.rglob('*'))
        dest=libs/path.name;shutil.copyfile(path,dest)
        records.append(dict(package=name,version=version,path=file,dll=r.digest(path),nupkg=r.digest(base/f'{name}.{version}.nupkg')))
        refs.append(f'<Reference Include="{path.stem}"><HintPath>{dest}</HintPath></Reference>')
    refs.append(f'<Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/proposal-library/Tedd.RTree.dll</HintPath></Reference>')
    project=r.ROOT/'Comparison.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><AssemblyName>Bench</AssemblyName><AssemblySearchPaths>{{HintPathFromItem}};{{RawFileName}}</AssemblySearchPaths><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><AllowUnsafeBlocks>true</AllowUnsafeBlocks><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{r.ROOT}/ComparisonWorker.cs"/><Compile Include="{r.REPO}/benchmarks/mutable-packed/NativeBench.cs"/>{''.join(refs)}</ItemGroup></Project>''')
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'comparison-artifacts','-o',r.ROOT/'comparison-caller','-p:UseSharedCompilation=false'],r.ROOT/'comparison-build.txt')
    assert r.digest(r.ROOT/'comparison-caller/Tedd.RTree.dll')==r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    (r.REPORT/'comparison-packages.json').write_text(json.dumps(records,indent=2))
    # Small counts, duplicate bounds, exact edge contacts, all/no hits. Same fixed library adapters.
    for n in (0,1,16,17):
        boxes=[(i%4-2,-1,i%4-1,1) for i in range(n)]
        qs=[(0,0,0,0),(-3,-2,3,2),(1,1,1,1),(100,100,101,101),(-2,-1,-2,-1),(-1,-1,0,1),(-3,-3,-2,-1),(2,1,2,1)]
        path=r.ROOT/f'comparison-boundary-{n}.txt';path.write_text(str(n)+'\n'+'\n'.join(' '.join(map(str,b)) for b in boxes+qs)+'\n')
        for mode in ('mutable','packed','rbush','nts-list','nts-visitor','rtree','enyim'):
            out,err,pid=r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'comparison-caller/Bench.dll',path,mode,'validate'],r.REPORT/f'boundary-{n}-{mode}.txt')
            if 'validated=8' not in err:raise RuntimeError('Boundary validation absent')
    print('All comparison adapter boundary checks pass.',flush=True)

def measure(phase):
    if phase=='confirmation':modes,blocks,seed,warm=['mutable','packed'],5,191048,False
    elif phase=='tiered':modes,blocks,seed,warm=['mutable','packed'],3,191049,True
    elif phase=='comparison':modes,blocks,seed,warm=['mutable','packed','rbush','nts-list','nts-visitor','rtree','enyim']+['direct-'+m for m in ('static','geo-hilbert','geo-str')]+['native-'+m for m in ('static','geo-hilbert','geo-str')],3,191050,False
    else:raise RuntimeError('Undeclared phase')
    dest=r.EVIDENCE/phase;dest.mkdir(exist_ok=False,parents=True)
    jobs=[(b,n,d,m) for b in range(blocks) for n in (1000,10000,100000) for d in ('uniform','clustered') for m in modes]
    random.Random(seed).shuffle(jobs)
    caller=r.ROOT/('comparison-caller' if phase=='comparison' else 'proposal-caller')
    native=r.ROOT/'retained/native/target/release'
    env=dict(r.ENV,PACKED_NATIVE_PATH=str(native/'packed_native.dll'))
    if warm:env.update(DOTNET_TieredCompilation='1',DOTNET_TieredPGO='1')
    runtime=Path('C:/Program Files/dotnet/shared/Microsoft.NETCore.App/10.0.13')
    protocol=dict(jobs=jobs,seed=seed,library=r.digest(caller/'Tedd.RTree.dll'),caller=r.digest(caller/'Bench.dll'),source=json.loads((r.REPORT/'selection.json').read_text()),
        driver=r.digest(__file__),runtime='10.0.13',affinity=4,tiering=warm,pgo=warm,warmup_seconds=3 if warm else None,observer='none',calibration_us=100000,
        runtime_hashes={n:r.digest(runtime/n) for n in ('coreclr.dll','clrjit.dll','System.Private.CoreLib.dll')},
        fixtures={f'{n}-{d}':r.digest(r.ROOT/f'retained/fixture-{n}-{d}.txt') for n in (1000,10000,100000) for d in ('uniform','clustered')},
        binary_hashes={p.name:r.digest(p) for p in caller.glob('*.dll')})
    if phase=='comparison':protocol.update(native_executable=r.digest(native/'packed-worker.exe'),native_library=r.digest(native/'packed_native.dll'),cargo_lock=r.digest(r.ROOT/'retained/native/Cargo.lock'),native_source={p.name:r.digest(p) for p in (r.ROOT/'retained/native/src').glob('*.rs')},static_zip=r.digest(r.ROOT/'retained/static.zip'),geo_zip=r.digest(r.ROOT/'retained/geo.zip'),packages=json.loads((r.REPORT/'comparison-packages.json').read_text()))
    (dest/'protocol.json').write_text(json.dumps(protocol,indent=2));shutil.copyfile(__file__,dest/'driver.py.txt')
    samples=[];launches=[]
    for i,(block,n,d,mode) in enumerate(jobs):
        fixture=r.ROOT/f'retained/fixture-{n}-{d}.txt'
        if mode.startswith('direct-'):cmd=[native/'packed-worker.exe',fixture,mode[7:]]
        else:cmd=[r.DOTNET,'exec','--fx-version','10.0.13',caller/'Bench.dll',fixture,mode]+(['warm'] if warm else [])
        started=time.time_ns();out,err,pid=r.run(cmd,dest/f'{i:03d}.out',env=env)
        expected=128 if mode=='mutable' and phase!='comparison' else 64
        if f'validated={expected}' not in err:raise RuntimeError('Validation absent')
        launches.append(dict(block=block,size=n,distribution=d,mode=mode,pid=pid,started_ns=started,validation=err.strip(),command=list(map(str,cmd))))
        for row in csv.reader(out.splitlines()):
            op,us,reps,alloc=row
            samples.append(dict(block=block,size=n,distribution=d,mode=mode,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        (dest/'samples.json').write_text(json.dumps(samples,indent=2));(dest/'launches.json').write_text(json.dumps(launches,indent=2))
        print(f'{i+1}/{len(jobs)} {phase} {mode} {n} {d}',flush=True)
    r.summarize(dest)

if __name__=='__main__':
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1]=='prepare-comparison':prepare_comparison()
        else:measure(sys.argv[1])
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)
