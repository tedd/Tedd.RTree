"""One prospectively bounded query inlining intervention after a regime guard failure."""
import sys
sys.dont_write_bytecode=True
import csv,ctypes,json,random,shutil,time
import research as r

def main():
    source=r.ROOT/'boundary-source/src/Tedd.RTree'
    shutil.copytree(r.ROOT/'proposal-source/src/Tedd.RTree',source)
    text=(source/'PackedRTree.cs').read_text().replace('PackedRTree','BoundaryPackedRTree')
    text=text.replace('    private int SearchLevel(', '    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]\n    private int SearchLevel(',1)
    (source/'BoundaryPackedRTree.cs').write_text(text,encoding='utf8',newline='\n')
    (r.REPORT/'BoundaryPackedRTree.cs').write_text(text,encoding='utf8',newline='\n')
    r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'boundary-artifacts','-o',r.ROOT/'boundary-library','-p:UseSharedCompilation=false'],r.ROOT/'boundary-build.txt')
    text=(r.ROOT/'ProposalWorker.cs').read_text().replace('    if (mode == "packed")','    if (mode == "boundary") return new BoundaryPackedRTree<int>(entries);\n    if (mode == "packed")',1)
    text=text.replace('ProposalChecks.Run();','BoundaryChecks.Run(); ProposalChecks.Run();',1)
    (r.ROOT/'BoundaryWorker.cs').write_text(text,encoding='utf8',newline='\n')
    project=r.ROOT/'BoundaryBench.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><AssemblyName>Bench</AssemblyName><AssemblySearchPaths>{{HintPathFromItem}};{{RawFileName}}</AssemblySearchPaths><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{r.ROOT}/BoundaryWorker.cs"/><Compile Include="{r.REPORT}/ProposalChecks.cs"/><Compile Include="{r.REPORT}/BoundaryChecks.cs"/><Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/boundary-library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''')
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'boundary-caller-artifacts','-o',r.ROOT/'boundary-caller','-p:UseSharedCompilation=false'],r.ROOT/'boundary-caller-build.txt')
    assert r.digest(r.ROOT/'boundary-caller/Tedd.RTree.dll')==r.digest(r.ROOT/'boundary-library/Tedd.RTree.dll')
    fixture=r.ROOT/'retained/fixture-10000-clustered.txt';caller=r.ROOT/'boundary-caller/Bench.dll'
    for scalar in (False,True):
        env=dict(r.ENV)
        if scalar:env['DOTNET_EnableHWIntrinsic']='0'
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',caller,fixture,'boundary','validate'],r.REPORT/f'boundary-semantic-{scalar}.txt',env=env)
    for mode in ('packed','boundary'):
        env=dict(r.ENV,DOTNET_TieredCompilation='1',DOTNET_TieredPGO='1',DOTNET_JitDisasm='*Search*',DOTNET_JitDisasmAssemblies='Tedd.RTree',DOTNET_JitStdOutFile=str(r.REPORT/f'boundary-{mode}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',caller,fixture,mode,'warm'],r.ROOT/f'boundary-{mode}-codegen.txt',env=env)
    dest=r.EVIDENCE/'boundary';dest.mkdir(exist_ok=False)
    jobs=[(b,tier,mode) for b in range(3) for tier in (False,True) for mode in ('mutable','packed','boundary')]
    random.Random(191051).shuffle(jobs)
    (dest/'protocol.json').write_text(json.dumps(dict(jobs=jobs,seed=191051,size=10000,distribution='clustered',affinity=4,observer='none',warmup_seconds=3,runtime='10.0.13',library=r.digest(r.ROOT/'boundary-caller/Tedd.RTree.dll'),caller=r.digest(caller),fixture=r.digest(fixture),source={p.name:r.digest(p) for p in source.glob('*.cs')},driver=r.digest(__file__)),indent=2))
    shutil.copyfile(__file__,dest/'driver.py.txt');samples=[];launches=[]
    for i,(block,tier,mode) in enumerate(jobs):
        env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0')
        cmd=[r.DOTNET,'exec','--fx-version','10.0.13',caller,fixture,mode]+(['warm'] if tier else [])
        started=time.time_ns();out,err,pid=r.run(cmd,dest/f'{i:03d}.out',env=env)
        assert f'validated={128 if mode=="mutable" else 64}' in err
        name=mode+('-tiered' if tier else '-fullopts')
        launches.append(dict(block=block,size=10000,distribution='clustered',mode=name,pid=pid,started_ns=started,validation=err.strip(),command=list(map(str,cmd))))
        for row in csv.reader(out.splitlines()):
            op,us,reps,allocated=row
            samples.append(dict(block=block,size=10000,distribution='clustered',mode=name,operation=op,us=float(us),repetitions=int(reps),allocated=float(allocated)))
        (dest/'samples.json').write_text(json.dumps(samples,indent=2));(dest/'launches.json').write_text(json.dumps(launches,indent=2))
        print(f'{i+1}/{len(jobs)} {name}',flush=True)
    r.summarize(dest)

if __name__=='__main__':
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        main()
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)
