"""One bounded compiler-boundary intervention after the recorded tiered guard failure."""
import sys
sys.dont_write_bytecode=True
import csv,ctypes,json,random,re,shutil,time
import study as r

def sizes(path):
    text=path.read_text();starts=list(re.finditer(r'^; Assembly listing for method (.+)$',text,re.M));found={}
    for i,m in enumerate(starts):
        header=m.group(1);body=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        if '(Tier1)' not in header or 'PackedRTree`1[int]' not in header:continue
        name='SearchLevel' if ':SearchLevel(' in header else 'Search' if ':Search(Tedd.RTree.Rectangle,System.Collections.Generic.List' in header else None
        match=re.search(r'Total bytes of code (\d+)',body)
        if name and match:found[name]=int(match.group(1))
    assert 'SearchLevel' in found,('Final Tier1 helper evidence unavailable',str(path),found)
    return found

def prepare():
    source=r.ROOT/'boundary-final-source/src/Tedd.RTree'
    shutil.copytree(r.ROOT/'final-source/src/Tedd.RTree',source)
    p=source/'PackedRTree.cs';text=p.read_text().replace('    private int SearchLevel(','''    // Keep recursive traversal from expanding into its callers under profile-guided inlining.
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    private int SearchLevel(''',1);p.write_text(text,encoding='utf8',newline='\n')
    shutil.copyfile(p,r.REPORT/'BoundaryFinalPackedRTree.cs')
    r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'boundary-final-artifacts','-o',r.ROOT/'boundary-final-library','-p:UseSharedCompilation=false'],r.ROOT/'boundary-final-build.txt')
    worker=(r.ROOT/'FinalWorker.cs').read_text().replace('"control" or "packed"','"control" or "packed" or "selected" or "boundary"')
    (r.ROOT/'BoundaryWorker.cs').write_text(worker)
    project=r.ROOT/'BoundaryCaller.csproj';refs=f'<Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/boundary-final-library/Tedd.RTree.dll</HintPath></Reference>'
    r.project(project,[r.ROOT/'BoundaryWorker.cs',r.REPORT/'PackedRTreeChecks.cs'],refs)
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'boundary-final-caller-artifacts','-o',r.ROOT/'boundary-caller','-p:UseSharedCompilation=false'],r.ROOT/'boundary-final-caller-build.txt')
    shutil.copytree(r.ROOT/'boundary-caller',r.ROOT/'selected-caller')
    shutil.copyfile(r.ROOT/'final-library/Tedd.RTree.dll',r.ROOT/'selected-caller/Tedd.RTree.dll')
    assert r.sha(r.ROOT/'selected-caller/Bench.dll')==r.sha(r.ROOT/'boundary-caller/Bench.dll')
    for scalar in (False,True):
        env=dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1')
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'boundary-caller/Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt','boundary','validate'],r.REPORT/f'boundary-final-checks-{scalar}.txt',env)
    diagnostics()

def diagnostics():
    code={}
    for mode in ('selected','boundary'):
        env=dict(r.ENV,DOTNET_TieredCompilation='1',DOTNET_TieredPGO='1',DOTNET_JitDisasm='*Search* *Query*',DOTNET_JitDisasmAssemblies='Tedd.RTree Bench',
            DOTNET_JitStdOutFile=str(r.REPORT/f'boundary-uniform-{mode}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/f'{mode}-caller/Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt',mode,'warm'],r.ROOT/f'boundary-uniform-{mode}-diagnostic.txt',env)
        code[mode]=sizes(r.REPORT/f'boundary-uniform-{mode}-jit.txt')
    r.atomic_json(r.REPORT/'boundary-code-size.json',code)
    print('Actual final Tier1 bytes',code,flush=True)

def measure():
    dest=r.EVIDENCE/'boundary';dest.mkdir(exist_ok=False)
    jobs=[(b,tier,m) for b in range(3) for tier in (False,True) for m in ('selected','boundary','mutable','rust')]
    random.Random(191071).shuffle(jobs)
    fixture=r.ROOT/'retained/fixture-10000-uniform.txt'
    callers={'selected':r.ROOT/'selected-caller','boundary':r.ROOT/'boundary-caller','mutable':r.ROOT/'selected-caller'}
    protocol=dict(jobs=jobs,seed=191071,runtime='10.0.13',affinity=4,observer='none',calibration_us=100000,warmup_seconds=3,
        driver=r.sha(__file__),fixture=r.sha(fixture),callers={m:{p.name:r.sha(p) for p in folder.glob('*.dll')} for m,folder in callers.items()},
        selected_source={p.name:r.sha(p) for p in (r.ROOT/'final-source/src/Tedd.RTree').glob('*.cs')},
        boundary_source={p.name:r.sha(p) for p in (r.ROOT/'boundary-final-source/src/Tedd.RTree').glob('*.cs')},
        native=r.sha(r.ROOT/'retained/native/target/release/packed-worker.exe'))
    r.atomic_json(dest/'protocol.json',protocol);shutil.copyfile(__file__,dest/'driver.py.txt')
    samples=[];launches=[]
    for i,(b,tier,m) in enumerate(jobs):
        if m=='rust':cmd=[r.ROOT/'retained/native/target/release/packed-worker.exe',fixture,'static']
        else:cmd=[r.DOTNET,'exec','--fx-version','10.0.13',callers[m]/'Bench.dll',fixture,m]+(['warm'] if tier else [])
        env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0')
        started=time.time_ns();out,err,pid=r.run(cmd,dest/f'{i:03d}.out',env);assert f'validated={128 if m=="mutable" else 64}' in err
        name=m+('-tiered' if tier else '-fullopts')
        launches.append(dict(block=b,size=10000,distribution='uniform',mode=name,pid=pid,started_ns=started,command=list(map(str,cmd)),validation=err.strip()))
        for op,us,reps,alloc in csv.reader(out.splitlines()):
            samples.append(dict(block=b,size=10000,distribution='uniform',mode=name,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        r.atomic_json(dest/'samples.json',samples);r.atomic_json(dest/'launches.json',launches)
        print(f'{i+1}/{len(jobs)} {name}',flush=True)
    r.summarize(dest)
    table={(v['mode'],v['operation']):v['median_us'] for v in json.loads((dest/'summary.json').read_text())}
    code=json.loads((r.REPORT/'boundary-code-size.json').read_text())
    code_ratio=code['boundary']['SearchLevel']/code['selected']['SearchLevel']
    ratios={suffix:table['boundary-'+suffix,'queries']/table['selected-'+suffix,'queries'] for suffix in ('tiered','fullopts')}
    mutable_ratio=table['boundary-tiered','queries']/table['mutable-tiered','queries']
    passed=code_ratio<=.6 and all(v<=1.05 for v in ratios.values()) and mutable_ratio<=1.10
    r.atomic_json(r.REPORT/'boundary-disposition.json',dict(passed=passed,code_ratio=code_ratio,query_ratios=ratios,mutable_ratio=mutable_ratio))
    print('Boundary gate',passed,code_ratio,ratios,mutable_ratio,flush=True)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    m=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(m,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if len(sys.argv)>1 and sys.argv[1]=='resume-diagnostics':diagnostics();measure()
        else:prepare();measure()
    finally:k.ReleaseMutex(m);k.CloseHandle(m)

if __name__=='__main__':main()
