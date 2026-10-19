"""Fresh repository-SDK confirmation and full comparator epoch; in-memory only."""
import sys
sys.dont_write_bytecode=True
import ctypes,difflib,json,os,shutil
from pathlib import Path
import study as r

FINAL=r.ROOT/'final-source/src/Tedd.RTree'
BASELINE=r.ROOT/'baseline-source/src/Tedd.RTree'

def prepare():
    shutil.copyfile(r.REPO/'global.json',r.ROOT/'global.json')
    r.run([r.DOTNET,'--version'],r.REPORT/'confirmation-sdk.txt')
    r.ENV.update(DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1')
    FINAL.mkdir(parents=True,exist_ok=False);BASELINE.mkdir(parents=True,exist_ok=False)
    for p in (r.REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,FINAL/p.name)
    for p in (r.ROOT/'proposal-source/src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,BASELINE/p.name)
    shutil.copyfile(r.REPO/'Research/2026-10-19-specialization/IReadOnlySpatialIndex.cs',FINAL/'IReadOnlySpatialIndex.cs')
    for suffix,kind,bounds in (('', 'RTree<T>', 'Rectangle'),('2D.Generic','RTree2D<TCoordinate, T>','Rectangle2D<TCoordinate>'),('3D.Generic','RTree3D<TCoordinate, T>','Box<TCoordinate>')):
        for prefix in ('','Snapshot','Concurrent'):
            path=FINAL/f'{prefix}RTree{suffix}.cs';text=path.read_text();decl='public sealed class '+prefix+kind
            contract=('IMutableSpatialIndex' if not prefix else 'IReadOnlySpatialIndex')+f'<{bounds}, T>'
            if prefix=='Concurrent':assert decl+' : IDisposable' in text;text=text.replace(decl+' : IDisposable',decl+' : IDisposable, '+contract,1)
            else:assert decl in text;text=text.replace(decl,decl+' : '+contract,1)
            path.write_text(text,encoding='utf8',newline='\n')
    selected=(r.REPORT/'VectorPackedRTree.cs').read_text().replace('VectorPackedRTree','PackedRTree').replace('KeyEncoding.Fill','PackedKeyEncoding.Fill')
    selected=selected.replace('        bool finiteX = double.IsFinite(scaleX), finiteY = double.IsFinite(scaleY);\n','')
    (FINAL/'PackedRTree.cs').write_text(selected,encoding='utf8',newline='\n')
    helper=(r.REPORT/'KeyEncoding.cs').read_text().replace('class KeyEncoding','class PackedKeyEncoding')
    helper=helper.replace('HilbertOrder.Encode(xy&Vector256.Create(65535u),xy>>>16)','PackedHilbertOrder.Encode(xy&Vector256.Create(65535u),xy>>>16)')
    helper=helper.replace('internal static class PackedKeyEncoding','''// Inputs are owned/exclusively leased spans of equal length. Vector loops only access
// complete four/eight-entry blocks; scalar tails preserve the public numeric contract.
internal static class PackedKeyEncoding''')
    (FINAL/'PackedKeyEncoding.cs').write_text(helper,encoding='utf8',newline='\n')
    prior=(BASELINE/'HilbertOrder.cs').read_text();begin=prior.index('    internal static Vector256<uint> Encode(')
    vector=prior[begin:prior.rfind('}')]
    (FINAL/'PackedHilbertOrder.cs').write_text('''using System.Runtime.Intrinsics;

namespace Tedd.RTree;

// Eight-lane form of the public-domain Hilbert transform used by HilbertOrder.
internal static class PackedHilbertOrder
{
'''+vector+'}\n',encoding='utf8',newline='\n')
    # Independent public API oracles: implementation-private helpers are not required.
    checks=(r.REPORT/'BinaryChecks.cs').read_text()
    start=checks.index('    internal static IReadOnlySpatialIndex');end=checks.index('    internal static void Run()',start)
    checks=checks[:start]+'''    internal static IReadOnlySpatialIndex<Rectangle,T> Build<T>(string mode,IReadOnlyList<SpatialEntry<T>> entries,int capacity=16,BulkLoadWorkspace? workspace=null)
        => new PackedRTree<T>(entries,capacity,workspace);
    internal static string[] Modes=["packed"];

'''+checks[end:]
    checks=checks.replace('BinaryChecks','PackedRTreeChecks').replace('        EncodingChecks.Run();\n','').replace('2047,2048,4099','2047,2048,2049,4099').replace('Binary variants:','Packed index:')
    (r.REPORT/'PackedRTreeChecks.cs').write_text(checks,encoding='utf8',newline='\n')
    worker=(r.REPO/'benchmarks/specialization/Worker.cs').read_text()
    start=worker.index('    if (mode == "mutable")');end=worker.index('\n}',start)
    worker=worker[:start]+'''    if (mode == "mutable") { var t=new RTree<int>();t.BulkLoad(entries);return t; }
    if (mode is "control" or "packed") return new PackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");'''+worker[end:]
    worker=worker.replace('ResearchChecks.Run(); ExtraChecks.Run();','PackedRTreeChecks.Run();')
    worker=worker.replace('Verify();\nif (action', '''Verify();
Console.Error.WriteLine("library="+Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(typeof(PackedRTree<int>).Assembly.Location))).ToLowerInvariant());
if (action''',1)
    (r.ROOT/'FinalWorker.cs').write_text(worker,encoding='utf8')
    for name,source in (('final',FINAL),('baseline',BASELINE)):
        r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/(name+'-artifacts'),'-o',r.ROOT/(name+'-library'),'-p:UseSharedCompilation=false'],r.ROOT/(name+'-build.txt'))
    refs=f'<Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/final-library/Tedd.RTree.dll</HintPath></Reference>'
    project=r.ROOT/'FinalBench.csproj';r.project(project,[r.ROOT/'FinalWorker.cs',r.REPORT/'PackedRTreeChecks.cs'],refs)
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'final-caller-artifacts','-o',r.ROOT/'final-caller','-p:UseSharedCompilation=false'],r.ROOT/'final-caller-build.txt')
    assert r.sha(r.ROOT/'final-caller/Tedd.RTree.dll')==r.sha(r.ROOT/'final-library/Tedd.RTree.dll')
    shutil.copytree(r.ROOT/'final-caller',r.ROOT/'baseline-caller')
    shutil.copyfile(r.ROOT/'baseline-library/Tedd.RTree.dll',r.ROOT/'baseline-caller/Tedd.RTree.dll')
    assert r.sha(r.ROOT/'baseline-caller/Bench.dll')==r.sha(r.ROOT/'final-caller/Bench.dll')
    main=(r.REPO/'tests/Tedd.RTree.Tests/Program.cs').read_text().replace('using Tedd.RTree;','using Tedd.RTree;\nPackedRTreeChecks.Run();\nProposalChecks.Run();',1)
    (r.ROOT/'FinalTestMain.cs').write_text(main)
    files=[p for p in (r.REPO/'tests/Tedd.RTree.Tests').glob('*.cs') if p.name!='Program.cs']+[r.ROOT/'FinalTestMain.cs',r.REPORT/'PackedRTreeChecks.cs',r.REPO/'Research/2026-10-19-specialization/ProposalChecks.cs']
    project=r.ROOT/'FinalTests.csproj';r.project(project,files,refs,'FinalTests')
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'final-tests-artifacts','-o',r.ROOT/'final-tests','-p:UseSharedCompilation=false'],r.ROOT/'final-tests-build.txt')
    for scalar in (False,True):
        env=dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1')
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'final-tests/FinalTests.dll'],r.REPORT/f'final-tests-{scalar}.txt',env)
        for mode,folder in (('control','baseline-caller'),('packed','final-caller')):
            r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/folder/'Bench.dll',r.ROOT/'retained/fixture-1000-uniform.txt',mode,'validate'],r.REPORT/f'final-{mode}-checks-{scalar}.txt',env)
    r.atomic_json(r.REPORT/'final-selection.json',dict(selected='VectorPackedRTree',experimental_source=r.sha(r.REPORT/'VectorPackedRTree.cs'),
        baseline_source={p.name:r.sha(p) for p in BASELINE.glob('*.cs')},source={p.name:r.sha(p) for p in FINAL.glob('*.cs')},
        original_production={p.name:r.sha(p) for p in (r.REPO/'src/Tedd.RTree').glob('*.cs')},sdk=(r.REPORT/'confirmation-sdk.txt').read_text(),
        caller=r.sha(r.ROOT/'final-caller/Bench.dll'),library=r.sha(r.ROOT/'final-library/Tedd.RTree.dll'),baseline_library=r.sha(r.ROOT/'baseline-library/Tedd.RTree.dll')))
    print('Frozen source, repository-SDK build, original/held-out/interface/fallback tests pass.',flush=True)

def confirm(phase):
    callers={'packed':r.ROOT/'final-caller','control':r.ROOT/'baseline-caller','mutable':r.ROOT/'final-caller'}
    if phase=='confirmation':modes,blocks,seed,tier,hw=['control','packed','rust'],5,191067,False,True
    elif phase=='tiered':modes,blocks,seed,tier,hw=['control','packed','mutable','rust'],3,191068,True,True
    elif phase=='fallback':modes,blocks,seed,tier,hw=['control','packed'],3,191069,False,False
    else:raise ValueError(phase)
    r.measure(phase,modes,blocks,seed,epoch='final',tiered=tier,callers=callers,source_root=FINAL,intrinsics=hw)
    dest=r.EVIDENCE/phase
    shutil.copyfile(__file__,dest/'finish-driver.py.txt')
    shutil.copyfile(r.REPORT/'final-selection.json',dest/'selection.json')

def codegen():
    for mode,folder in (('control','baseline-caller'),('packed','final-caller')):
        for tier in (False,True):
            env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0',
                DOTNET_JitDisasm='*Search* *.ctor* *Fill* *Encode* *Query*',DOTNET_JitDisasmAssemblies='Tedd.RTree Bench',
                DOTNET_JitStdOutFile=str(r.REPORT/f'final-{mode}-{tier}-jit.txt'))
            r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/folder/'Bench.dll',r.ROOT/'retained/fixture-10000-clustered.txt',mode,'warm' if tier else 'codegen'],r.ROOT/f'final-{mode}-{tier}-codegen.txt',env)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    m=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(m,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1]=='prepare':prepare();codegen()
        elif sys.argv[1]=='validate-performance':
            for phase in ('confirmation','tiered','fallback'):confirm(phase)
        else:confirm(sys.argv[1])
    finally:k.ReleaseMutex(m);k.CloseHandle(m)

if __name__=='__main__':main()
