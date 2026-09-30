"""Dependent measurement sequence; run only with the shared performance lock."""
import pathlib
import subprocess
import os
import json
import datetime

RUN = pathlib.Path(__file__).resolve().parent
ROOT = RUN.parents[1]
RAW = RUN / 'raw'
start = datetime.datetime.now(datetime.timezone.utc).isoformat()

def execute(command, name, env=None):
    print('Executing:', command, flush=True)
    with (RAW / (name + '.txt')).open('w', encoding='utf-8') as output:
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        print((RAW / (name + '.txt')).read_text(), flush=True)
        raise SystemExit(result.returncode)

execute(['dotnet', 'build', str(RUN / 'Investigation.csproj'), '-c', 'Release'], 'followup-build')
dll = str(RUN / 'bin/Release/net10.0/Investigation.dll')
execute(['dotnet', dll, '--screen', str(RAW / 'followup-screen.csv')], 'followup-screen')
execute(['dotnet', dll, '--generic-screen', str(RAW / 'generic-repeat-screen.csv')], 'generic-repeat-screen')
execute(['dotnet', dll, '--local-array-screen', str(RAW / 'local-array-screen.csv')], 'local-array-screen')
for pattern, name in (('*Search*', 'search'), ('*CollectValues*', 'collector')):
    env = dict(os.environ, DOTNET_JitDisasm=pattern, DOTNET_JitDisasmAssemblies='Investigation', DOTNET_JitDisasmDiffable='1')
    execute(['dotnet', dll, '--disasm'], 'tiered-' + name, env)
trace = pathlib.Path.home() / '.dotnet/tools/dotnet-trace.exe'
execute([str(trace), 'collect', '--providers', 'Microsoft-DotNETCore-SampleProfiler', '--format', 'Speedscope',
         '--output', str(RAW / 'final.nettrace'), '--', 'dotnet', dll, '--profile-after'], 'final-profile')
(RAW / 'followup-lock-window.json').write_text(json.dumps({'startUtc': start,
    'endUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'lock': str(pathlib.Path.home() / '.codex/locks/performance-measurement.lock')}, indent=2))
