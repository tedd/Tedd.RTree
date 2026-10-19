"""Independent confirmation of the least intrusive passing query-JIT policy."""
import sys
sys.dont_write_bytecode=True
import ctypes,json,shutil
import study as r

FINAL=r.ROOT/'final-source/src/Tedd.RTree'

def prepare():
    disposition=json.loads((r.REPORT/'jit-policy-disposition.json').read_text());selected=disposition['selected'];assert selected
    for name in ('final-source','final-library','final-caller'):shutil.copytree(r.ROOT/name,r.ROOT/('prepolicy-'+name))
    shutil.copyfile(r.REPORT/'final-selection.json',r.REPORT/'boundary-final-selection.json')
    shutil.copyfile(r.ROOT/f'{selected}-source/src/Tedd.RTree/PackedRTree.cs',FINAL/'PackedRTree.cs')
    r.run([r.DOTNET,'build',FINAL/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'policy-promotion-library-artifacts','-o',r.ROOT/'final-library','-p:UseSharedCompilation=false'],r.ROOT/'policy-promotion-build.txt')
    r.run([r.DOTNET,'build',r.ROOT/'FinalBench.csproj','-c','Release','--artifacts-path',r.ROOT/'policy-promotion-caller-artifacts','-o',r.ROOT/'final-caller','-p:UseSharedCompilation=false'],r.ROOT/'policy-promotion-caller-build.txt')
    assert r.sha(r.ROOT/'final-library/Tedd.RTree.dll')==r.sha(r.ROOT/'final-caller/Tedd.RTree.dll')
    shutil.copytree(r.ROOT/'final-caller',r.ROOT/'baseline-caller',dirs_exist_ok=True);shutil.copyfile(r.ROOT/'baseline-library/Tedd.RTree.dll',r.ROOT/'baseline-caller/Tedd.RTree.dll')
    r.run([r.DOTNET,'build',r.ROOT/'FinalTests.csproj','-c','Release','--artifacts-path',r.ROOT/'policy-promotion-test-artifacts','-o',r.ROOT/'policy-promotion-tests','-p:UseSharedCompilation=false'],r.ROOT/'policy-promotion-test-build.txt')
    assert r.sha(r.ROOT/'policy-promotion-tests/Tedd.RTree.dll')==r.sha(r.ROOT/'final-library/Tedd.RTree.dll')
    for scalar in (False,True):
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'policy-promotion-tests/FinalTests.dll'],r.REPORT/f'policy-promotion-tests-{scalar}.txt',dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1'))
    selection=json.loads((r.REPORT/'final-selection.json').read_text())
    selection.update(selected='Vector normalization + NoInlining + '+selected,confirmation_suffix='-3',
        source={p.name:r.sha(p) for p in FINAL.glob('*.cs')},caller=r.sha(r.ROOT/'final-caller/Bench.dll'),library=r.sha(r.ROOT/'final-library/Tedd.RTree.dll'),
        supersedes='boundary-final-selection.json',jit_policy_disposition=disposition)
    r.atomic_json(r.REPORT/'final-selection.json',selection)
    for tier in (False,True):
        env=dict(r.ENV,DOTNET_TieredCompilation='1' if tier else '0',DOTNET_TieredPGO='1' if tier else '0',DOTNET_JitDisasm='*Search* *Fill* *Encode* *Query*',DOTNET_JitDisasmAssemblies='Tedd.RTree Bench',
            DOTNET_JitStdOutFile=str(r.REPORT/f'policy-promotion-packed-{tier}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'final-caller/Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt','packed','warm' if tier else 'codegen'],r.ROOT/f'policy-promotion-packed-{tier}-diagnostic.txt',env)
    print('Query JIT-policy source frozen; original/interface/held-out/fallback tests pass.',flush=True)

def confirm():
    callers={'packed':r.ROOT/'final-caller','control':r.ROOT/'baseline-caller','mutable':r.ROOT/'final-caller'}
    for phase,modes,blocks,seed,tier,hw in (
        ('confirmation-3',['control','packed','rust'],5,191076,False,True),
        ('tiered-3',['control','packed','mutable','rust'],3,191077,True,True),
        ('fallback-3',['control','packed'],3,191078,False,False)):
        r.measure(phase,modes,blocks,seed,epoch='final',tiered=tier,callers=callers,source_root=FINAL,intrinsics=hw)
        shutil.copyfile(__file__,r.EVIDENCE/phase/'policy-promotion-driver.py.txt');shutil.copyfile(r.REPORT/'final-selection.json',r.EVIDENCE/phase/'selection.json')

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        prepare();confirm()
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)

if __name__=='__main__':main()
