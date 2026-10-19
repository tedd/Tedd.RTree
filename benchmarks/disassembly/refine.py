"""R10: hoisted query and direct AVX lane permutations, in an isolated copy."""
import sys
sys.dont_write_bytecode = True
import csv
import ctypes
import json
import random
import shutil
import statistics
import study as r

def build():
    source = r.ROOT/'tuned-source'
    source.mkdir(exist_ok=False)
    for p in (r.REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs', '.csproj'):
            shutil.copyfile(p, source/p.name)
    text = (source/'PackedRTree.cs').read_text()
    text = text.replace('using System.Runtime.Intrinsics;', '''using System.Runtime.Intrinsics;
using System.Runtime.Intrinsics.X86;
using System.Runtime.CompilerServices;''', 1)
    old = '''            for (int j = 0; j < boxes.Length; j++)
                if (boxes[j].Intersects(bounds)) { results.Add(_values[start + j]); found++; }'''
    assert text.count(old) == 1
    replacement = '''            if (Avx.IsSupported)
            {
                var q = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in bounds)));
                var mask = Vector256.Create(-1L).AsDouble();
                for (int j = 0; j < boxes.Length; j++)
                {
                    var b = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in boxes[j])));
                    var left = Avx.InsertVector128(b, q.GetLower(), 1);
                    var right = Avx.Permute2x128(q, b, 0x31);
                    var match = Avx.Compare(right, left, FloatComparisonMode.UnorderedNotLessThanSignaling);
                    if (Avx.TestC(match, mask)) { results.Add(_values[start + j]); found++; }
                }
            }
            else
            {
                for (int j = 0; j < boxes.Length; j++)
                    if (boxes[j].Intersects(bounds)) { results.Add(_values[start + j]); found++; }
            }'''
    text = text.replace(old, replacement)
    (source/'PackedRTree.cs').write_text(text, encoding='utf8')
    (r.REPORT/'TunedPackedRTree.cs').write_text(text, encoding='utf8')
    r.run([r.DOTNET, 'build', source/'Tedd.RTree.csproj', '-c', 'Release', '--artifacts-path',
           r.ROOT/'tuned-artifacts', '-o', r.ROOT/'tuned-library', '-p:UseSharedCompilation=false'], 'tuned-build.txt')
    tests = r.ROOT/'tuned-tests'
    shutil.copytree(r.ROOT/'tests', tests)
    shutil.copyfile(r.ROOT/'tuned-library/Tedd.RTree.dll', tests/'Tedd.RTree.dll')
    for hw in ('1', '0'):
        r.run([r.DOTNET, 'exec', '--fx-version', '10.0.13', tests/'Tedd.RTree.Tests.dll'],
              f'tuned-tests-hardware-{hw}.txt', dict(r.ENV, DOTNET_EnableHWIntrinsic=hw))
    for mode, base in (('tuned', 'list'), ('tuned-simd', 'simd')):
        out = r.ROOT/f'caller-{mode}'
        shutil.copytree(r.ROOT/f'caller-{base}', out)
        shutil.copyfile(r.ROOT/'tuned-library/Tedd.RTree.dll', out/'Tedd.RTree.dll')
        r.run([r.DOTNET, 'exec', '--fx-version', '10.0.13', out/'Bench.dll',
               r.ROOT/'retained/fixture-1000-uniform.txt', 'packed'], f'{mode}-jit.txt',
              dict(r.ENV, DOTNET_JitDisasm='*SearchLevel* *b__2*', DOTNET_JitDisasmAssemblies='Tedd.RTree Bench'))
    r.save('refinement-build.json', dict(library=r.sha(r.ROOT/'tuned-library/Tedd.RTree.dll'),
                                        source=r.sha(source/'PackedRTree.cs')))
    print('R10 builds and full hardware/fallback tests pass; emitted code retained.', flush=True)

def measure():
    dest = r.REPORT/'refinement'
    dest.mkdir(exist_ok=False)
    modes = ['list', 'simd', 'tuned', 'tuned-simd', 'rust']
    jobs = [(b,n,d,m) for b in range(3) for n in (1000,10000,100000)
            for d in ('uniform','clustered') for m in modes]
    random.Random(191080).shuffle(jobs)
    native = r.ROOT/'retained/native/target/release/packed-worker.exe'
    protocol = dict(jobs=jobs, seed=191080, driver=r.sha(__file__), shared_driver=r.sha(r.__file__),
                    identities={m:dict(caller=r.sha(r.ROOT/f'caller-{m}/Bench.dll'),library=r.sha(r.ROOT/f'caller-{m}/Tedd.RTree.dll'))
                                for m in modes if m!='rust'}, native=r.sha(native),
                    runtime='10.0.13',affinity=4,tiering=False,pgo=False,observer='none',calibration_us=100000)
    r.save('refinement-protocol.json', protocol)
    samples = []
    for i,(block,n,dist,mode) in enumerate(jobs):
        fixture = r.ROOT/f'retained/fixture-{n}-{dist}.txt'
        cmd = [native,fixture,'static'] if mode=='rust' else [r.DOTNET,'exec','--fx-version','10.0.13',
               r.ROOT/f'caller-{mode}/Bench.dll',fixture,'packed']
        out = r.run(cmd,f'refinement/{i:03d}.txt',dict(r.ENV,DOTNET_EnableHWIntrinsic='1'))
        assert 'validated=64' in (dest/f'{i:03d}.txt').read_text()
        for operation,us,repetitions,allocated in csv.reader(out.splitlines()):
            samples.append(dict(block=block,size=n,distribution=dist,mode=mode,operation=operation,
                                us=float(us),repetitions=int(repetitions),allocated=None if allocated=='NA' else float(allocated)))
        r.save('refinement-samples.json',samples)
        print(f'{i+1}/{len(jobs)} {mode} {n} {dist}',flush=True)
    summary = []
    for n in (1000,10000,100000):
        for dist in ('uniform','clustered'):
            for mode in modes:
                for operation in ('build','queries'):
                    values = [sum(s['us'] for s in samples if s['size']==n and s['distribution']==dist
                                  and s['mode']==mode and s['block']==b
                                  and (s['operation']=='build' if operation=='build' else s['operation'].startswith('query')))
                              for b in range(3)]
                    summary.append(dict(size=n,distribution=dist,mode=mode,operation=operation,
                                        median_us=statistics.median(values),min_us=min(values),max_us=max(values),count=3))
    r.save('refinement-summary.json',summary)

def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1]=='build':build()
        elif sys.argv[1]=='measure':measure()
        else:raise ValueError(sys.argv[1])
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)

if __name__=='__main__':main()
