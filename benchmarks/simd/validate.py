"""Final repository checks with all disposable output under the task root."""
import ctypes
from pathlib import Path
import zipfile
import sys
sys.dont_write_bytecode = True
import driver

root = driver.ROOT
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateMutexW.restype = ctypes.c_void_p
kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
mutex = kernel.CreateMutexW(None, False, 'Global\\Tedd.RTree.PerformanceHost')
if kernel.WaitForSingleObject(mutex, 1000) not in (0, 0x80): raise RuntimeError('Performance host busy')
try:
    artifacts = root/'repository-artifacts'
    output = driver.RESEARCH/'repository-validation'
    output.mkdir(exist_ok=True)
    if len(sys.argv)>1 and sys.argv[1]=='adapters':
        caller=root/'adapter-caller'
        driver.run([driver.DOTNET,'build',driver.REPO/'benchmarks/csharp-charts/Bench.csproj','-c','Release',
                    '--artifacts-path',root/'adapter-artifacts','-o',caller,'-p:UseSharedCompilation=false'],output/'adapter-build.txt')
        for distribution in ('uniform','clustered'):
            for mode in ('candidate','rbush','nts-list','nts-visitor','rtree','enyim'):
                result=driver.run([driver.DOTNET,'exec','--fx-version','10.0.13',caller/'Bench.dll',
                                  root/f'fixture-10000-{distribution}.txt',mode,'validate'],output/f'adapter-{mode}-{distribution}.txt')
                if 'validated=64' not in result.stderr: raise RuntimeError('Adapter validation missing')
        print('All six managed adapters validate exact IDs and timed checksums on both fixtures.',flush=True)
        sys.exit(0)
    driver.run([driver.DOTNET, 'build', driver.REPO/'Tedd.RTree.sln', '-c', 'Release',
                '--artifacts-path', artifacts, '-p:UseSharedCompilation=false'], output/'solution-build.txt', timeout=240)
    tests = artifacts/'bin/Tedd.RTree.Tests/release/Tedd.RTree.Tests.dll'
    for scalar in (False, True):
        env = dict(driver.ENV)
        if scalar: env['DOTNET_EnableHWIntrinsic'] = '0'
        driver.run([driver.DOTNET, 'exec', '--fx-version', '10.0.13', tests],
                    output/f'tests-{scalar}.txt', env=env)
    driver.run([driver.DOTNET,'pack',driver.REPO/'src/Tedd.RTree/Tedd.RTree.csproj','-c','Release','--no-build',
                '--artifacts-path',artifacts,'-o',root/'packages'],output/'package.txt')
    package = next((root/'packages').glob('*.nupkg'))
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if 'lib/net10.0/Tedd.RTree.dll' not in names: raise RuntimeError('Missing managed package assembly')
        if any(n.startswith('runtimes/') or n.endswith(('.so','.dylib')) for n in names):
            raise RuntimeError('Unexpected native package payload')
        (output/'package-contents.txt').write_text('\n'.join(names)+'\n')
    print('Release solution, hardware/scalar tests, and managed package checks passed.', flush=True)
finally:
    kernel.ReleaseMutex(mutex)
    kernel.CloseHandle(mutex)
