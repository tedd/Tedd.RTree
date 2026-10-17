"""Serial benchmark driver. Artifacts and scratch must be explicitly designated."""
import csv
import ctypes
import json
import os
from pathlib import Path
import random
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
phase = sys.argv[3]
if not root.is_relative_to(Path('D:/Workspaces/AI').resolve()):
    raise SystemExit('Invalid task workspace')
destination.mkdir(parents=True, exist_ok=True)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 4):
    raise ctypes.WinError(ctypes.get_last_error())
fixtures = []
for n in (1000, 10000, 100000):
    for distribution in ('uniform', 'clustered'):
        state = 73211
        def next_int(limit):
            global state
            state = (state * 1664525 + 1013904223) & 0xffffffff
            return (state >> 8) % limit
        boxes = []
        for i in range(n):
            x = i % 8 * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            y = i % 8 * 125 + next_int(30) if distribution == 'clustered' else next_int(1000)
            boxes.append((x, y, x + next_int(5) + 1, y + next_int(5) + 1))
        queries = []
        for i in range(64):
            x, y = next_int(1000), next_int(1000)
            width = (0, 20, 200, 1000)[i % 4]
            queries.append((x, y, x + width, y + width))
        fixture = root / f'{n}-{distribution}.txt'
        fixture.write_text(str(n) + '\n' + '\n'.join(' '.join(map(str, b)) for b in boxes + queries) + '\n', encoding='ascii')
        fixtures.append((n, distribution, str(fixture)))
workers = {
    'control': ['dotnet', str(root / 'control-worker/Bench.dll'), '{fixture}'],
    'algorithm': ['dotnet', str(root / 'algorithm-worker/Bench.dll'), '{fixture}'],
    'candidate': ['dotnet', str(root / 'candidate-worker/Bench.dll'), '{fixture}'],
    'layout': ['dotnet', str(root / 'layout-worker/Bench.dll'), '{fixture}'],
}
for stage in ('copy', 'input', 'radix', 'inline'):
    workers[stage] = ['dotnet', str(root / f'{stage}-worker/Bench.dll'), '{fixture}']
if phase == 'algorithm':
    names, rounds = ['control', 'algorithm'], 3
elif phase == 'layout':
    names, rounds = ['algorithm', 'candidate'], 3
elif phase == 'copy':
    names, rounds = ['algorithm', 'layout', 'candidate'], 3
elif phase in ('input', 'radix'):
    names, rounds = ['copy' if phase == 'input' else 'input', 'candidate'], 3
    for name in names: workers[name] = workers[name] + ['build-only']
elif phase in ('inline', 'span'):
    names, rounds = ['radix' if phase == 'inline' else 'inline', 'candidate'], 3
    for name in names: workers[name] = workers[name] + ['query-only']
elif phase == 'confirmation':
    names, rounds = ['control', 'candidate'], 5
    for mode in ('static', 'geo-hilbert', 'geo-str'):
        workers['native-' + mode] = [str(root / 'native/target/release/packed-worker.exe'), '{fixture}', mode]
        workers['interop-' + mode] = ['dotnet', str(root / 'candidate-worker/Bench.dll'), '{fixture}', 'native-' + mode]
        names += ['native-' + mode, 'interop-' + mode]
else:
    raise SystemExit('Unknown phase')
jobs = [(r, n, distribution, fixture, name) for r in range(rounds) for n, distribution, fixture in fixtures for name in names]
random.Random({'algorithm': 31191, 'layout': 81921, 'copy': 21833, 'input': 59117, 'radix': 77621,
               'inline': 18313, 'span': 44819, 'confirmation': 99183}[phase]).shuffle(jobs)
env = dict(os.environ, DOTNET_TieredCompilation='0', GOMAXPROCS='1',
           PACKED_NATIVE_PATH=str(root / 'native/target/release/packed_native.dll'))
samples = []
(destination / 'protocol.json').write_text(json.dumps(dict(phase=phase, rounds=rounds, jobs=jobs,
    workers=workers, environment={'DOTNET_TieredCompilation':'0','PACKED_NATIVE_PATH':env['PACKED_NATIVE_PATH']},
    affinity_mask=4, minimum_calibration_ms=100, observer='no EventPipe collection during timing'), indent=2))
for index, (round_number, n, distribution, fixture, name) in enumerate(jobs):
    command = [a.replace('{fixture}', fixture) for a in workers[name]]
    process = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=180)
    if process.returncode or 'validated=' not in process.stderr:
        raise RuntimeError((command, process.stdout, process.stderr))
    for row in csv.reader(process.stdout.splitlines()):
        op, microseconds, iterations, allocation = row
        samples.append(dict(library=name, size=n, distribution=distribution, round=round_number,
            operation=op, microseconds=float(microseconds), iterations=int(iterations), allocation_bytes=None if allocation == 'NA' else float(allocation)))
    (destination / 'samples.json').write_text(json.dumps(samples, indent=2))
    print(f'{index+1}/{len(jobs)} {name} {n} {distribution}', flush=True)
