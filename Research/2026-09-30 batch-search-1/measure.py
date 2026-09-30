"""Inspected local-only driver; invoke exclusively through run_with_performance_lock.py."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1].parent
RUN = pathlib.Path(__file__).resolve().parent
RAW = RUN / 'raw'
RAW.mkdir(exist_ok=True)

def execute(command, name, env=None):
    print('Executing:', command, flush=True)
    with (RAW / (name + '.txt')).open('w', encoding='utf-8') as output:
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        print((RAW / (name + '.txt')).read_text(encoding='utf-8'), flush=True)
        raise SystemExit(result.returncode)

stage = sys.argv[1]
execute(['dotnet', '--info'], stage + '-environment')
execute(['dotnet', 'build', str(RUN / 'Investigation.csproj'), '-c', 'Release', '--nologo'], stage + '-build')
execute(['dotnet', 'run', '--project', 'tests/Tedd.RTree.Tests', '-c', 'Release'], stage + '-tests')
dll = str(RUN / 'bin/Release/net10.0/Investigation.dll')
if stage == 'baseline':
    trace = pathlib.Path.home() / '.dotnet/tools/dotnet-trace.exe'
    execute([str(trace), 'collect', '--providers', 'Microsoft-DotNETCore-SampleProfiler', '--format', 'Speedscope',
             '--output', str(RAW / 'baseline.nettrace'), '--', 'dotnet', dll, '--profile'], 'baseline-profile')
execute(['dotnet', dll, '--screen', str(RAW / (stage + '-screen.csv'))], stage + '-screen')
if stage == 'candidates':
    execute(['dotnet', dll, '--build-screen', str(RAW / 'construction-screen.csv')], 'construction-screen')
if stage == 'confirmation':
    execute(['dotnet', dll, '--generic-screen', str(RAW / 'generic-screen.csv')], 'generic-screen')
    execute(['dotnet', dll, '--filter', '*TraversalBenchmarks*', '*BatchBenchmarks*',
             '--artifacts', str(RAW / 'bdn')], 'confirmation-bdn')
    env = dict(os.environ, DOTNET_JitDisasm='*Search*', DOTNET_JitDisasmAssemblies='Investigation',
               DOTNET_JitDisasmDiffable='1')
    execute(['dotnet', dll, '--disasm'], 'tiered-disassembly', env)
    trace = pathlib.Path.home() / '.dotnet/tools/dotnet-trace.exe'
    execute([str(trace), 'collect', '--providers', 'Microsoft-DotNETCore-SampleProfiler', '--format', 'Speedscope',
             '--output', str(RAW / 'final.nettrace'), '--', 'dotnet', dll, '--profile-after'], 'final-profile')
