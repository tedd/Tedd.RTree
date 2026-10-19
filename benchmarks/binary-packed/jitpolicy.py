"""Bounded initial-JIT-tier policy experiment after two independent regime failures."""
import sys
sys.dont_write_bytecode=True
import csv,ctypes,json,random,shutil,time
import study as r

def prepare():
    baseline=r.ROOT/'final-source/src/Tedd.RTree'
    for mode in ('private-opt','public-opt'):
        source=r.ROOT/f'{mode}-source/src/Tedd.RTree';shutil.copytree(baseline,source)
        p=source/'PackedRTree.cs';text=p.read_text()
        flag='System.Runtime.CompilerServices.MethodImplOptions.NoInlining'
        flags=flag+' | System.Runtime.CompilerServices.MethodImplOptions.AggressiveOptimization'
        text=text.replace(flag,flags,1)
        if mode=='public-opt':text=text.replace('    public int Search(Rectangle bounds, List<T> results)',
            '    [System.Runtime.CompilerServices.MethodImpl('+flags+')]\n    public int Search(Rectangle bounds, List<T> results)',1)
        p.write_text(text,encoding='utf8',newline='\n');shutil.copyfile(p,r.REPORT/f'{mode}-PackedRTree.cs')
        r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/f'{mode}-artifacts','-o',r.ROOT/f'{mode}-library','-p:UseSharedCompilation=false'],r.ROOT/f'{mode}-build.txt')
    worker=(r.ROOT/'FinalWorker.cs').read_text()
    worker=worker.replace('if (mode is "control" or "packed")','if (mode is "control" or "packed" or "selected" or "private-opt" or "public-opt")')
    (r.ROOT/'PolicyWorker.cs').write_text(worker)
    project=r.ROOT/'PolicyCaller.csproj';refs=f'<Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/private-opt-library/Tedd.RTree.dll</HintPath></Reference>'
    r.project(project,[r.ROOT/'PolicyWorker.cs',r.REPORT/'PackedRTreeChecks.cs'],refs)
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'policy-caller-artifacts','-o',r.ROOT/'policy-caller','-p:UseSharedCompilation=false'],r.ROOT/'policy-caller-build.txt')
    proof={}
    for mode,library in (('selected','final-library'),('private-opt','private-opt-library'),('public-opt','public-opt-library')):
        caller=r.ROOT/f'policy-{mode}-caller';shutil.copytree(r.ROOT/'policy-caller',caller);shutil.copyfile(r.ROOT/library/'Tedd.RTree.dll',caller/'Tedd.RTree.dll')
        if mode!='selected':
            for scalar in (False,True):
                env=dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1')
                r.run([r.DOTNET,'exec','--fx-version','10.0.13',caller/'Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt',mode,'validate'],r.REPORT/f'{mode}-checks-{scalar}.txt',env)
        env=dict(r.ENV,DOTNET_TieredCompilation='1',DOTNET_TieredPGO='1',DOTNET_JitDisasm='*Search* *Query*',DOTNET_JitDisasmAssemblies='Tedd.RTree Bench',
            DOTNET_JitStdOutFile=str(r.REPORT/f'policy-{mode}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',caller/'Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt',mode,'warm'],r.ROOT/f'policy-{mode}-diagnostic.txt',env)
        headers=[line for line in (r.REPORT/f'policy-{mode}-jit.txt').read_text().splitlines() if line.startswith('; Assembly listing') and 'PackedRTree`1[int]' in line]
        helper=[line for line in headers if ':SearchLevel(' in line]
        entry=[line for line in headers if ':Search(Tedd.RTree.Rectangle,System.Collections.Generic.List' in line]
        if mode!='selected':assert helper and all('(FullOpts)' in line for line in helper)
        if mode=='public-opt':assert entry and all('(FullOpts)' in line for line in entry)
        proof[mode]=dict(helper=helper,entry=entry)
    r.atomic_json(r.REPORT/'jit-policy-code.json',proof)
    print('Immediate optimized-code policy verified.',flush=True)

def measure():
    dest=r.EVIDENCE/'jit-policy';dest.mkdir(exist_ok=False)
    jobs=[(b,tier,m) for b in range(3) for tier in (False,True) for m in ('selected','private-opt','public-opt','mutable','rust')]
    random.Random(191075).shuffle(jobs);fixture=r.ROOT/'retained/fixture-10000-uniform.txt'
    callers={m:r.ROOT/f'policy-{m}-caller' for m in ('selected','private-opt','public-opt')};callers['mutable']=callers['selected']
    r.atomic_json(dest/'protocol.json',dict(jobs=jobs,seed=191075,runtime='10.0.13',affinity=4,observer='none',warmup_seconds=3,calibration_us=100000,driver=r.sha(__file__),fixture=r.sha(fixture),
        callers={m:{p.name:r.sha(p) for p in folder.glob('*.dll')} for m,folder in callers.items()},
        sources={mode:{p.name:r.sha(p) for p in (r.ROOT/f'{mode}-source/src/Tedd.RTree').glob('*.cs')} for mode in ('private-opt','public-opt')}))
    shutil.copyfile(__file__,dest/'driver.py.txt');samples=[];launches=[]
    for i,(b,tier,m) in enumerate(jobs):
        cmd=[r.ROOT/'retained/native/target/release/packed-worker.exe',fixture,'static'] if m=='rust' else [r.DOTNET,'exec','--fx-version','10.0.13',callers[m]/'Bench.dll',fixture,m]+(['warm'] if tier else [])
        env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0')
        started=time.time_ns();out,err,pid=r.run(cmd,dest/f'{i:03d}.out',env);assert f'validated={128 if m=="mutable" else 64}' in err
        mode=m+('-tiered' if tier else '-fullopts')
        launches.append(dict(block=b,size=10000,distribution='uniform',mode=mode,pid=pid,started_ns=started,command=list(map(str,cmd)),validation=err.strip()))
        for op,us,reps,alloc in csv.reader(out.splitlines()):samples.append(dict(block=b,size=10000,distribution='uniform',mode=mode,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        r.atomic_json(dest/'samples.json',samples);r.atomic_json(dest/'launches.json',launches)
        print(f'{i+1}/{len(jobs)} {mode}',flush=True)
    r.summarize(dest);table={(v['mode'],v['operation']):v['median_us'] for v in json.loads((dest/'summary.json').read_text())}
    dispositions={}
    for mode in ('private-opt','public-opt'):
        regime=table[mode+'-tiered','queries']/table[mode+'-fullopts','queries']
        mutable=table[mode+'-tiered','queries']/table['mutable-tiered','queries']
        full=table[mode+'-fullopts','queries']/table['selected-fullopts','queries']
        dispositions[mode]=dict(passed=regime<=1.10 and mutable<=1.10 and full<=1.05,regime_ratio=regime,mutable_ratio=mutable,fullopts_ratio=full)
    selected=next((m for m in ('private-opt','public-opt') if dispositions[m]['passed']),None)
    r.atomic_json(r.REPORT/'jit-policy-disposition.json',dict(selected=selected,dispositions=dispositions));print('JIT policy disposition',selected,dispositions,flush=True)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        prepare();measure()
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)

if __name__=='__main__':main()
