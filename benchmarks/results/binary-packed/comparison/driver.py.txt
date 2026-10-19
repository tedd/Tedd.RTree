"""Complete retained-library comparison; explicit fixture IO and in-memory indexes."""
import sys
sys.dont_write_bytecode=True
import csv,ctypes,json,random,shutil,time
from pathlib import Path
import study as r

MODES=['mutable','packed','rbush','nts-list','nts-visitor','rtree','enyim']+['direct-'+m for m in ('static','geo-hilbert','geo-str')]+['native-'+m for m in ('static','geo-hilbert','geo-str')]

def prepare():
    text=(r.REPO/'benchmarks/csharp-charts/Worker.cs').read_text()
    marker='var index = Indexes.Prepare(args[1], boxes, queries);'
    text=text.replace(marker,'if (args[1].StartsWith("native-")) { NativeBench.Run(boxes, queries, args[1]); return; }\n'+marker)
    first=text.index('            case "candidate":');last=text.index('            case "rbush":',first)
    text=text[:first]+'''            case "mutable":
            case "packed":
                var entries=boxes.Select((b,i)=>new SpatialEntry<int>(b,i)).ToArray();
                var result=new List<int>(boxes.Length);
                return new Prepared<IReadOnlySpatialIndex<Rectangle,int>,Rectangle>(()=>{
                    if(mode=="packed")return new PackedRTree<int>(entries);
                    var tree=new Tedd.RTree.RTree<int>(16);tree.BulkLoad(entries);return tree;
                },queries,(tree,query)=>{result.Clear();tree.Search(query,result);long sum=0;foreach(int id in result)sum+=id+1;return sum;},
                    (tree,query)=>tree.Search(query));
'''+text[last:]
    (r.ROOT/'ComparisonWorker.cs').write_text(text,encoding='utf8')
    libraries=r.ROOT/'comparison-libraries';libraries.mkdir(exist_ok=False)
    packages=[('rbush','4.0.0','lib/net8.0/RBush.dll'),('nettopologysuite','2.6.0','lib/netstandard2.1/NetTopologySuite.dll'),('rtree','1.1.0','lib/netstandard2.0/RTree.dll'),('enyim.collections.rtree','1.0.5','lib/net45/Enyim.Collections.RTree.dll')]
    refs=[];records=[]
    for name,version,file in packages:
        base=Path('C:/Users/tedd/.nuget/packages')/name/version;path=base/file
        assert not any(p.suffix.lower() in ('.targets','.props','.exe','.ps1') for p in base.rglob('*'))
        dest=libraries/path.name;shutil.copyfile(path,dest)
        refs.append(f'<Reference Include="{path.stem}"><HintPath>{dest}</HintPath></Reference>')
        records.append(dict(package=name,version=version,file=file,dll=r.sha(path),nupkg=r.sha(base/f'{name}.{version}.nupkg')))
    refs.append(f'<Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/final-library/Tedd.RTree.dll</HintPath></Reference>')
    project=r.ROOT/'Comparison.csproj'
    r.project(project,[r.ROOT/'ComparisonWorker.cs',r.REPO/'benchmarks/mutable-packed/NativeBench.cs'],''.join(refs))
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'comparison-artifacts','-o',r.ROOT/'comparison-caller','-p:UseSharedCompilation=false'],r.ROOT/'comparison-build.txt')
    assert r.sha(r.ROOT/'comparison-caller/Tedd.RTree.dll')==r.sha(r.ROOT/'final-library/Tedd.RTree.dll')
    r.atomic_json(r.REPORT/'comparison-packages.json',records)
    for n in (0,1,16,17):
        boxes=[(i%4-2,-1,i%4-1,1) for i in range(n)]
        queries=[(0,0,0,0),(-3,-2,3,2),(1,1,1,1),(100,100,101,101),(-2,-1,-2,-1),(-1,-1,0,1),(-3,-3,-2,-1),(2,1,2,1)]
        fixture=r.ROOT/f'comparison-boundary-{n}.txt'
        fixture.write_text(str(n)+'\n'+'\n'.join(' '.join(map(str,b)) for b in boxes+queries)+'\n')
        for mode in MODES[:7]:
            _,err,_=r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'comparison-caller/Bench.dll',fixture,mode,'validate'],r.REPORT/f'comparison-boundary-{n}-{mode}.txt')
            assert 'validated=8' in err
    print('All comparator boundary/adapter checks pass.',flush=True)

def measure():
    dest=r.EVIDENCE/'comparison';dest.mkdir(parents=True,exist_ok=False)
    jobs=[(b,n,d,m) for b in range(3) for n in (1000,10000,100000) for d in ('uniform','clustered') for m in MODES]
    random.Random(191070).shuffle(jobs)
    caller=r.ROOT/'comparison-caller';native=r.ROOT/'retained/native/target/release'
    env=dict(r.ENV,DOTNET_TieredCompilation='0',DOTNET_TieredPGO='0',DOTNET_EnableHWIntrinsic='1',PACKED_NATIVE_PATH=str(native/'packed_native.dll'))
    runtime=Path('C:/Program Files/dotnet/shared/Microsoft.NETCore.App/10.0.13')
    protocol=dict(jobs=jobs,seed=191070,driver=r.sha(__file__),runtime='10.0.13',affinity=4,tiering=False,pgo=False,observer='none',calibration_us=100000,
        libraries={p.name:r.sha(p) for p in caller.glob('*.dll')},source=json.loads((r.REPORT/'final-selection.json').read_text()),
        fixtures={p.name:r.sha(p) for p in (r.ROOT/'retained').glob('fixture-*.txt')},
        runtime_hashes={n:r.sha(runtime/n) for n in ('coreclr.dll','clrjit.dll','System.Private.CoreLib.dll')},
        native_executable=r.sha(native/'packed-worker.exe'),native_library=r.sha(native/'packed_native.dll'),cargo_lock=r.sha(r.ROOT/'retained/native/Cargo.lock'),
        static_zip=r.sha(r.ROOT/'retained/static.zip'),geo_zip=r.sha(r.ROOT/'retained/geo.zip'),packages=json.loads((r.REPORT/'comparison-packages.json').read_text()))
    r.atomic_json(dest/'protocol.json',protocol);shutil.copyfile(__file__,dest/'driver.py.txt')
    samples=[];launches=[]
    for i,(b,n,d,m) in enumerate(jobs):
        fixture=r.ROOT/f'retained/fixture-{n}-{d}.txt'
        cmd=[native/'packed-worker.exe',fixture,m[7:]] if m.startswith('direct-') else [r.DOTNET,'exec','--fx-version','10.0.13',caller/'Bench.dll',fixture,m]
        started=time.time_ns();out,err,pid=r.run(cmd,dest/f'{i:03d}.out',env)
        assert 'validated=64' in err
        launches.append(dict(block=b,size=n,distribution=d,mode=m,pid=pid,started_ns=started,command=list(map(str,cmd)),validation=err.strip()))
        for op,us,reps,alloc in csv.reader(out.splitlines()):
            samples.append(dict(block=b,size=n,distribution=d,mode=m,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        r.atomic_json(dest/'samples.json',samples);r.atomic_json(dest/'launches.json',launches)
        print(f'{i+1}/{len(jobs)} {m} {n} {d}',flush=True)
    r.summarize(dest)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='measure':measure()
        elif sys.argv[1]=='all':prepare();measure()
        else:raise ValueError(sys.argv[1])
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)

if __name__=='__main__':main()
