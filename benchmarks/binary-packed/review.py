"""Validate the exact staged patch in a disposable copy; never changes the main checkout."""
import sys
sys.dont_write_bytecode=True
import ctypes,json,shutil
from pathlib import Path
import study as r

def validate():
    root=r.ROOT/'review-source';assert not root.exists()
    for folder in ('src/Tedd.RTree','tests/Tedd.RTree.Tests'):
        dest=root/folder;dest.mkdir(parents=True)
        for p in (r.REPO/folder).iterdir():
            if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,dest/p.name)
    for name in ('README.md','LICENSE','global.json'):shutil.copyfile(r.REPO/name,root/name)
    for change in json.loads((r.REPORT/'integration-plan.json').read_text()):
        original=r.REPO/change['path'];before=r.sha(original) if original.exists() else None
        assert before==change['before_sha256']
        src=r.ROOT/'integration'/change['path'];assert r.sha(src)==change['after_sha256']
        dest=root/change['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    library=root/'src/Tedd.RTree/Tedd.RTree.csproj'
    r.run([r.DOTNET,'build',library,'-c','Release','--artifacts-path',r.ROOT/'review-library-artifacts','-o',r.ROOT/'review-library','-p:UseSharedCompilation=false'],r.ROOT/'review-library-build.txt')
    r.run([r.DOTNET,'build',root/'tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj','-c','Release','--artifacts-path',r.ROOT/'review-test-artifacts','-o',r.ROOT/'review-tests','-p:UseSharedCompilation=false'],r.ROOT/'review-tests-build.txt')
    for scalar in (False,True):
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'review-tests/Tedd.RTree.Tests.dll'],r.REPORT/f'review-tests-{scalar}.txt',dict(r.ENV,DOTNET_EnableHWIntrinsic='0' if scalar else '1'))
    project=r.ROOT/'VerifyIL.csproj';r.project(project,[r.REPO/'benchmarks/binary-packed/VerifyIL.cs'],assembly='VerifyIL')
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'verify-il-artifacts','-o',r.ROOT/'verify-il','-p:UseSharedCompilation=false'],r.ROOT/'verify-il-build.txt')
    r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'verify-il/VerifyIL.dll',r.ROOT/'review-library/Tedd.RTree.dll',r.ROOT/'final-library/Tedd.RTree.dll'],r.REPORT/'review-il-equivalence.txt')
    r.atomic_json(r.REPORT/'review-validation.json',dict(main_checkout_changed=False,
        patch=r.sha(r.REPORT/'implementation.patch'),plan=r.sha(r.REPORT/'integration-plan.json'),
        review_library=r.sha(r.ROOT/'review-library/Tedd.RTree.dll'),frozen_library=r.sha(r.ROOT/'final-library/Tedd.RTree.dll'),
        tests_hardware=True,tests_fallback=True,il_equivalence=True))
    print('Exact staged patch passes original/new tests and frozen IL/flag equivalence in the isolated copy.',flush=True)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    m=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(m,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:validate()
    finally:k.ReleaseMutex(m);k.CloseHandle(m)

if __name__=='__main__':main()
