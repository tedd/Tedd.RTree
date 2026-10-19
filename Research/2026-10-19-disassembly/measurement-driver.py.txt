"""Inspected in-memory builds and external static/generated-code diagnostics."""
import sys
sys.dont_write_bytecode = True
import ctypes
import hashlib
import json
import os
from pathlib import Path
import csv
import random
import shutil
import statistics
import subprocess
import time
import zipfile

REPO = Path(__file__).resolve().parents[2]
ROOT = Path('D:/Workspaces/AI/rtree-disassembly-20261019')
REPORT = REPO / 'Research/2026-10-19-disassembly'
OLD = REPO / 'Research/2026-10-19-binary-packed'
DOTNET = Path('C:/Program Files/dotnet/dotnet.exe')
OBJDUMP = Path('C:/Program Files/Microsoft Visual Studio/18/Insiders/VC/Tools/Llvm/x64/bin/llvm-objdump.exe')
ENV = dict(os.environ, TEMP=str(ROOT), TMP=str(ROOT),
           DOTNET_CLI_HOME=str(ROOT/'cli-home'), DOTNET_CLI_TELEMETRY_OPTOUT='1',
           DOTNET_TieredCompilation='0', DOTNET_TieredPGO='0',
           CORECLR_ENABLE_PROFILING='0', COR_ENABLE_PROFILING='0')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(name, obj):
    (REPORT/name).write_text(json.dumps(obj, indent=2), encoding='utf8')

def run(cmd, name, env=None, timeout=300):
    command = list(map(str, cmd))
    started = time.time_ns()
    p = subprocess.Popen(command, cwd=ROOT, env=env or ENV,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    with (REPORT/'launches.jsonl').open('a', encoding='utf8') as f:
        f.write(json.dumps(dict(pid=p.pid, started_ns=started,
                               command=command, log=name))+'\n')
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()
        raise
    (REPORT/name).write_bytes(out+b'\nSTDERR:\n'+err)
    if p.returncode:
        raise RuntimeError((command, p.returncode, err[-2000:], out[-2000:]))
    return out.decode('utf8', errors='replace')

def restore():
    archive = OLD/'reproduction.zip'
    manifest = json.loads((OLD/'reproduction.manifest.json').read_text())
    assert sha(archive) == manifest['archive_sha256']
    records = {}
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if not (name.startswith(('retained/', 'comparison-caller/', 'final-caller/'))
                    or name in ('ComparisonWorker.cs', 'Worker.cs')):
                continue
            data = z.read(name)
            assert hashlib.sha256(data).hexdigest() == manifest['files'][name]['sha256']
            path = ROOT/name
            assert path.resolve().is_relative_to(ROOT.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            records[name] = manifest['files'][name]
    shutil.copyfile(REPO/'global.json', ROOT/'global.json')
    save('restored.json', records)

def validate():
    plan = json.loads((OLD/'integration-plan.json').read_text())
    for item in plan:
        assert sha(REPO/item['path']) == item['after_sha256'], item['path']
    run([DOTNET, '--version'], 'sdk.txt')
    run([DOTNET, 'build', REPO/'src/Tedd.RTree/Tedd.RTree.csproj', '-c', 'Release',
         '--artifacts-path', ROOT/'library-artifacts', '-o', ROOT/'library',
         '-p:UseSharedCompilation=false'], 'library-build.txt')
    run([DOTNET, 'build', REPO/'tests/Tedd.RTree.Tests/Tedd.RTree.Tests.csproj',
         '-c', 'Release', '--artifacts-path', ROOT/'test-artifacts',
         '-o', ROOT/'tests', '-p:UseSharedCompilation=false'], 'tests-build.txt')
    for hw in ('1', '0'):
        run([DOTNET, 'exec', '--fx-version', '10.0.13',
             ROOT/'tests/Tedd.RTree.Tests.dll'], f'tests-hardware-{hw}.txt',
            dict(ENV, DOTNET_EnableHWIntrinsic=hw))
    save('integration-validation.json', dict(
        branch='main', files=len(plan), patch=sha(OLD/'implementation.patch'),
        library=sha(ROOT/'library/Tedd.RTree.dll'),
        tests_hardware=True, tests_fallback=True))
    print('Applied implementation builds and all hardware/fallback checks pass.', flush=True)

def disassemble():
    assert OBJDUMP.is_file()
    run([OBJDUMP, '--version'], 'objdump-version.txt')
    records = {}
    native = ROOT/'retained/native/target/release'
    for name in ('packed-worker.exe', 'packed_native.dll'):
        path = native/name
        records[name] = sha(path)
        run([OBJDUMP, '--syms', '--private-headers', path], name+'-headers.txt')
        run([OBJDUMP, '--disassemble', '--demangle', '--x86-asm-syntax=intel', path], name+'-disassembly.txt')
    for dist in ('uniform', 'clustered'):
        env = dict(ENV, DOTNET_JitDisasm='*Search* *Query* *Bench* *Measure* *Construct* *Fill* *IntrospectiveSort* *IntroSort* *Partition* *Encode* *Sum*',
                   DOTNET_JitDisasmAssemblies='Tedd.RTree Bench System.Private.CoreLib')
        run([DOTNET, 'exec', '--fx-version', '10.0.13', ROOT/'comparison-caller/Bench.dll',
             ROOT/f'retained/fixture-1000-{dist}.txt', 'packed'], f'managed-{dist}-jit.txt', env)
    # Upstream source is provenance for the exact retained binaries, never executed.
    with zipfile.ZipFile(ROOT/'retained/static.zip') as z:
        for name in z.namelist():
            if not name.endswith('.rs'):
                continue
            path = ROOT/'upstream-static'/name
            assert path.resolve().is_relative_to((ROOT/'upstream-static').resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(z.read(name))
    save('diagnostic-identities.json', dict(
        native=records, disassembler=sha(OBJDUMP),
        caller=sha(ROOT/'comparison-caller/Bench.dll'),
        library=sha(ROOT/'comparison-caller/Tedd.RTree.dll'),
        runtime='10.0.13', tiering=False, pgo=False, observer='JitDisasm',
        note='Diagnostic stdout timings are not quiet timing observations.'))
    print('Exact retained native disassembly and managed generated-code diagnostics complete.', flush=True)

def caller_code():
    env = dict(ENV, DOTNET_JitDisasm='*', DOTNET_JitDisasmAssemblies='Tedd.RTree Bench')
    run([DOTNET, 'exec', '--fx-version', '10.0.13', ROOT/'comparison-caller/Bench.dll',
         ROOT/'retained/fixture-1000-uniform.txt', 'packed'], 'managed-caller-all-jit.txt', env)

def project(path, items, references='', assembly='Bench'):
    path.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><AssemblyName>{assembly}</AssemblyName><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems><AllowUnsafeBlocks>true</AllowUnsafeBlocks></PropertyGroup><ItemGroup>{''.join(f'<Compile Include="{p}"/>' for p in items)}{references}</ItemGroup></Project>''', encoding='utf8')

def build_interventions():
    source = ROOT/'leaf-source'
    source.mkdir(exist_ok=False)
    for p in (REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs', '.csproj'):
            shutil.copyfile(p, source/p.name)
    text = (source/'PackedRTree.cs').read_text()
    text = text.replace('using System.Runtime.Intrinsics;', '''using System.Runtime.Intrinsics;
using System.Runtime.Intrinsics.X86;
using System.Runtime.CompilerServices;''', 1)
    old = 'if (boxes[j].Intersects(bounds)) { results.Add(_values[start + j]); found++; }'
    assert text.count(old) == 1
    text = text.replace(old, 'if (LeafIntersects(in boxes[j], in bounds)) { results.Add(_values[start + j]); found++; }')
    marker = '    /// <inheritdoc/>\n    public List<T> Search'
    assert text.count(marker) == 1
    helper = '''    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static bool LeafIntersects(in Rectangle box, in Rectangle query)
    {
        if (!Avx.IsSupported) return box.Intersects(query);
        var b = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in box)));
        var q = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in query)));
        var left = Vector256.Create(b.GetLower(), q.GetLower());
        var right = Vector256.Create(q.GetUpper(), b.GetUpper());
        return Avx.MoveMask(Avx.CompareLessThanOrEqual(left, right)) == 15;
    }

'''
    text = text.replace(marker, helper+marker)
    (source/'PackedRTree.cs').write_text(text, encoding='utf8')
    (REPORT/'LeafPackedRTree.cs').write_text(text, encoding='utf8')
    run([DOTNET, 'build', source/'Tedd.RTree.csproj', '-c', 'Release',
         '--artifacts-path', ROOT/'leaf-artifacts', '-o', ROOT/'leaf-library',
         '-p:UseSharedCompilation=false'], 'leaf-library-build.txt')
    # Use the unchanged existing test caller with only the changed dependency DLL.
    tests = ROOT/'leaf-tests'
    shutil.copytree(ROOT/'tests', tests)
    shutil.copyfile(ROOT/'leaf-library/Tedd.RTree.dll', tests/'Tedd.RTree.dll')
    for hw in ('1', '0'):
        run([DOTNET, 'exec', '--fx-version', '10.0.13', tests/'Tedd.RTree.Tests.dll'],
            f'leaf-tests-hardware-{hw}.txt', dict(ENV, DOTNET_EnableHWIntrinsic=hw))
    original = (ROOT/'ComparisonWorker.cs').read_text()
    consume = 'long sum=0;foreach(int id in result)sum+=id+1;return sum;'
    assert original.count(consume) == 1
    records = {}
    for mode in ('list', 'span', 'simd'):
        caller = ROOT/f'caller-{mode}.cs'
        caller.write_text(original if mode == 'list' else original.replace(consume, f'return Checksum.{"Span" if mode=="span" else "Vector"}(result);'), encoding='utf8')
        libs = ROOT/'comparison-caller'
        refs = ''.join(f'<Reference Include="{p.stem}"><HintPath>{p}</HintPath></Reference>'
                       for p in libs.glob('*.dll') if p.name not in ('Bench.dll', 'Tedd.RTree.dll'))
        refs += f'<Reference Include="Tedd.RTree"><HintPath>{ROOT}/library/Tedd.RTree.dll</HintPath></Reference>'
        proj = ROOT/f'caller-{mode}.csproj'
        project(proj, [caller, REPO/'benchmarks/disassembly/Checksum.cs', REPO/'benchmarks/mutable-packed/NativeBench.cs'], refs)
        out = ROOT/f'caller-{mode}'
        run([DOTNET, 'build', proj, '-c', 'Release', '--artifacts-path', ROOT/f'caller-{mode}-artifacts',
             '-o', out, '-p:UseSharedCompilation=false'], f'caller-{mode}-build.txt')
        records[mode] = dict(source=sha(caller), caller=sha(out/'Bench.dll'), library=sha(out/'Tedd.RTree.dll'))
    for name, base in (('leaf', 'list'), ('combined', 'simd')):
        shutil.copytree(ROOT/f'caller-{base}', ROOT/f'caller-{name}')
        shutil.copyfile(ROOT/'leaf-library/Tedd.RTree.dll', ROOT/f'caller-{name}/Tedd.RTree.dll')
    for mode in ('list', 'span', 'simd', 'leaf', 'combined'):
        env = dict(ENV, DOTNET_JitDisasm='*SearchLevel* *b__2* *Span* *Vector*', DOTNET_JitDisasmAssemblies='Tedd.RTree Bench')
        run([DOTNET, 'exec', '--fx-version', '10.0.13', ROOT/f'caller-{mode}/Bench.dll',
             ROOT/'retained/fixture-1000-uniform.txt', 'packed'], f'intervention-{mode}-jit.txt', env)
    save('intervention-builds.json', dict(callers=records, leaf_library=sha(ROOT/'leaf-library/Tedd.RTree.dll'),
                                        checksum=sha(REPO/'benchmarks/disassembly/Checksum.cs')))
    print('Interventions built; full public hardware/fallback checks and code diagnostics complete.', flush=True)

def measure_interventions():
    dest = REPORT/'measurements'
    dest.mkdir(exist_ok=False)
    modes = ['list', 'span', 'simd', 'leaf', 'combined', 'rust']
    jobs = [(b, n, d, m) for b in range(3) for n in (1000, 10000, 100000)
            for d in ('uniform', 'clustered') for m in modes]
    random.Random(191079).shuffle(jobs)
    native = ROOT/'retained/native/target/release/packed-worker.exe'
    identities = {m: dict(caller=sha(ROOT/f'caller-{m}/Bench.dll'), library=sha(ROOT/f'caller-{m}/Tedd.RTree.dll'))
                  for m in modes if m != 'rust'}
    save('quiet-protocol.json', dict(seed=191079, jobs=jobs, driver=sha(__file__), identities=identities,
         native=sha(native), affinity=4, tiering=False, pgo=False, runtime='10.0.13', observer='none',
         calibration_us=100000, fixtures={p.name:sha(p) for p in (ROOT/'retained').glob('fixture-*.txt')}))
    samples = []
    for i, (block, n, dist, mode) in enumerate(jobs):
        fixture = ROOT/f'retained/fixture-{n}-{dist}.txt'
        cmd = [native, fixture, 'static'] if mode == 'rust' else [DOTNET, 'exec', '--fx-version', '10.0.13',
               ROOT/f'caller-{mode}/Bench.dll', fixture, 'packed']
        out = run(cmd, f'measurements/{i:03d}.txt', dict(ENV, DOTNET_EnableHWIntrinsic='1'))
        log = (dest/f'{i:03d}.txt').read_text()
        assert 'validated=64' in log
        for operation, us, repetitions, allocated in csv.reader(out.splitlines()):
            samples.append(dict(block=block, size=n, distribution=dist, mode=mode, operation=operation,
                                us=float(us), repetitions=int(repetitions), allocated=None if allocated=='NA' else float(allocated)))
        save('samples.json', samples)
        print(f'{i+1}/{len(jobs)} {mode} {n} {dist}', flush=True)
    keys = sorted({(s['size'], s['distribution'], s['mode'], s['operation']) for s in samples})
    summary = []
    for n, dist, mode, operation in keys:
        rows = [s for s in samples if (s['size'],s['distribution'],s['mode'],s['operation'])==(n,dist,mode,operation)]
        values = [s['us'] for s in rows]
        summary.append(dict(size=n, distribution=dist, mode=mode, operation=operation,
                            median_us=statistics.median(values), min_us=min(values), max_us=max(values), count=len(values)))
    for n in (1000,10000,100000):
        for dist in ('uniform','clustered'):
            for mode in modes:
                values = [sum(s['us'] for s in samples if s['size']==n and s['distribution']==dist and s['mode']==mode
                              and s['block']==b and s['operation'].startswith('query')) for b in range(3)]
                summary.append(dict(size=n, distribution=dist, mode=mode, operation='queries',
                                    median_us=statistics.median(values),min_us=min(values),max_us=max(values),count=3))
    save('summary.json', summary)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateMutexW.restype = ctypes.c_void_p
    k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    k.ReleaseMutex.argtypes = [ctypes.c_void_p]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    mutex = k.CreateMutexW(None, False, 'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex, 1000) not in (0, 0x80):
        raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(), 4):
            raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1] == 'prepare':
            restore(); validate()
        elif sys.argv[1] == 'disassemble':
            disassemble()
        elif sys.argv[1] == 'caller-code':
            caller_code()
        elif sys.argv[1] == 'build-interventions':
            build_interventions()
        elif sys.argv[1] == 'measure-interventions':
            measure_interventions()
        else:
            raise ValueError(sys.argv[1])
    finally:
        k.ReleaseMutex(mutex); k.CloseHandle(mutex)

if __name__ == '__main__':
    main()
