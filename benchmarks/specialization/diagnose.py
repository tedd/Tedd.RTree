"""Fresh rebuild and tiered code evidence, isolated from all quiet observations."""
import sys
sys.dont_write_bytecode=True
import ctypes,json
import research as r

def main():
    source=r.ROOT/'proposal-source/src/Tedd.RTree'
    expected=json.loads((r.REPORT/'selection.json').read_text())['source']
    assert {p.name:r.digest(p) for p in source.glob('*.cs')}==expected
    before=r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','-t:Rebuild','--artifacts-path',r.ROOT/'proposal-artifacts','-o',r.ROOT/'proposal-library','-p:UseSharedCompilation=false'],r.ROOT/'proposal-fresh-rebuild.txt')
    after=r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    (r.REPORT/'fresh-build.json').write_text(json.dumps(dict(before=before,after=after,identical=before==after,caller_copy=r.digest(r.ROOT/'proposal-caller/Tedd.RTree.dll')),indent=2))
    assert before==after==r.digest(r.ROOT/'proposal-caller/Tedd.RTree.dll')
    for mode in ('mutable','packed'):
        dest=r.REPORT/f'ordinary-{mode}-jit.txt'
        if dest.exists():raise RuntimeError('Diagnostic already exists')
        env=dict(r.ENV,DOTNET_TieredCompilation='1',DOTNET_TieredPGO='1',DOTNET_JitDisasm='*Search* *Encode* *Query*',DOTNET_JitStdOutFile=str(dest))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'proposal-caller/Bench.dll',r.ROOT/'retained/fixture-10000-clustered.txt',mode,'warm'],r.REPORT/f'ordinary-{mode}-diagnostic.txt',env=env)
    print('Fresh source/binary identity and ordinary-tiering diagnostics retained.',flush=True)

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
