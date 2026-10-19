"""Freeze and independently confirm the changed compiler-boundary source."""
import sys
sys.dont_write_bytecode=True
import ctypes,json,shutil
import study as r

FINAL=r.ROOT/'final-source/src/Tedd.RTree'

def prepare():
    assert json.loads((r.REPORT/'boundary-disposition.json').read_text())['passed']
    for name in ('final-source','final-library','final-caller'):
        shutil.copytree(r.ROOT/name,r.ROOT/('vector-'+name))
    shutil.copyfile(r.REPORT/'final-selection.json',r.REPORT/'vector-final-selection.json')
    shutil.copyfile(r.ROOT/'boundary-final-source/src/Tedd.RTree/PackedRTree.cs',FINAL/'PackedRTree.cs')
    r.run([r.DOTNET,'build',FINAL/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'promotion-library-artifacts','-o',r.ROOT/'final-library','-p:UseSharedCompilation=false'],r.ROOT/'promotion-build.txt')
    r.run([r.DOTNET,'build',r.ROOT/'FinalBench.csproj','-c','Release','--artifacts-path',r.ROOT/'promotion-caller-artifacts','-o',r.ROOT/'final-caller','-p:UseSharedCompilation=false'],r.ROOT/'promotion-caller-build.txt')
    assert r.sha(r.ROOT/'final-library/Tedd.RTree.dll')==r.sha(r.ROOT/'final-caller/Tedd.RTree.dll')
    shutil.copytree(r.ROOT/'final-caller',r.ROOT/'baseline-caller',dirs_exist_ok=True)
    shutil.copyfile(r.ROOT/'baseline-library/Tedd.RTree.dll',r.ROOT/'baseline-caller/Tedd.RTree.dll')
    r.run([r.DOTNET,'build',r.ROOT/'FinalTests.csproj','-c','Release','--artifacts-path',r.ROOT/'promotion-test-artifacts','-o',r.ROOT/'promotion-tests','-p:UseSharedCompilation=false'],r.ROOT/'promotion-test-build.txt')
    assert r.sha(r.ROOT/'promotion-tests/Tedd.RTree.dll')==r.sha(r.ROOT/'final-library/Tedd.RTree.dll')
    for scalar in (False,True):
        env=dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1')
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'promotion-tests/FinalTests.dll'],r.REPORT/f'promotion-tests-{scalar}.txt',env)
    selection=json.loads((r.REPORT/'final-selection.json').read_text())
    selection.update(selected='Vector normalization + recursive NoInlining boundary',
        source={p.name:r.sha(p) for p in FINAL.glob('*.cs')},caller=r.sha(r.ROOT/'final-caller/Bench.dll'),library=r.sha(r.ROOT/'final-library/Tedd.RTree.dll'),
        supersedes='vector-final-selection.json',boundary_disposition=json.loads((r.REPORT/'boundary-disposition.json').read_text()))
    r.atomic_json(r.REPORT/'final-selection.json',selection)
    for tier in (False,True):
        env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0',DOTNET_JitDisasm='*Search* *Fill* *Encode* *Query*',DOTNET_JitDisasmAssemblies='Tedd.RTree Bench',
            DOTNET_JitStdOutFile=str(r.REPORT/f'promotion-packed-{tier}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'final-caller/Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt','packed','warm' if tier else 'codegen'],r.ROOT/f'promotion-packed-{tier}-diagnostic.txt',env)
    print('Changed source frozen; original/held-out/interface/fallback tests pass.',flush=True)

def confirm():
    callers={'packed':r.ROOT/'final-caller','control':r.ROOT/'baseline-caller','mutable':r.ROOT/'final-caller'}
    for phase,modes,blocks,seed,tier,hw in (
        ('confirmation-2',['control','packed','rust'],5,191072,False,True),
        ('tiered-2',['control','packed','mutable','rust'],3,191073,True,True),
        ('fallback-2',['control','packed'],3,191074,False,False)):
        r.measure(phase,modes,blocks,seed,epoch='final',tiered=tier,callers=callers,source_root=FINAL,intrinsics=hw)
        shutil.copyfile(__file__,r.EVIDENCE/phase/'promotion-driver.py.txt')
        shutil.copyfile(r.REPORT/'final-selection.json',r.EVIDENCE/phase/'selection.json')

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    m=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(m,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        prepare();confirm()
    finally:k.ReleaseMutex(m);k.CloseHandle(m)

if __name__=='__main__':main()
