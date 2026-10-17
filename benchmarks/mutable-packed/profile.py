"""Owned persistent DotNetLab MCP session; CLI call mode cannot retain asynchronous jobs."""
import ctypes
import json
import hashlib
import shutil
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(sys.argv[1]).resolve()
host = Path('D:/Workspaces/AI/dotnetlab-installations/9c23369/Tedd.DotNetLab.Host.dll')
catalog = root / 'lab'
destination = Path(sys.argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=True)
stage = sys.argv[3] if len(sys.argv) > 3 else 'algorithm-worker'
identity_tag = stage + '-' + hashlib.sha256((root / stage / 'Tedd.RTree.dll').read_bytes()).hexdigest()[:12]
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateMutexW.restype = ctypes.c_void_p
kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
mutex = kernel.CreateMutexW(None, False, 'Global\\Tedd.RTree.PerformanceHost')
if kernel.WaitForSingleObject(mutex, 1000) not in (0, 0x80):
    raise RuntimeError('Benchmark host is busy')
try:
    for phase in ('query', 'build'):
        output = destination / phase
        output.mkdir(exist_ok=True)
        env = dict(os.environ, DOTNET_TieredCompilation='0', DOTNET_JitDisasm='*Search* *BulkLoad* *CollectValues* *SortIndices* *Encode*',
                   DOTNET_JitDisasmAssemblies='Tedd.RTree', DOTNET_JitStdOutFile=str(output / 'jit.txt'))
        with (root / f'profile-{phase}-persistent.out').open('w') as stdout, (root / f'profile-{phase}-persistent.err').open('w') as stderr:
            target = subprocess.Popen(['dotnet', 'exec', '--fx-version', '10.0.13', str(root / stage / 'Bench.dll'),
                                      str(root / '100000-uniform.txt'), 'profile-' + phase],
                                     env=env, cwd=root, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
            server = None
            try:
                kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                if not kernel.SetProcessAffinityMask(int(target._handle), 4):
                    raise ctypes.WinError(ctypes.get_last_error())
                grant_process = subprocess.run(['dotnet', str(host), 'grant', str(catalog), str(target.pid), 'observe', '120', '3'], capture_output=True, text=True, check=True)
                grant = json.loads(grant_process.stdout)
                server = subprocess.Popen(['dotnet', str(host), 'serve', str(catalog)], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=(root / f'lab-{phase}.err').open('w'), text=True, encoding='utf8', creationflags=subprocess.CREATE_NO_WINDOW)
                counter = 0
                def rpc(method, params):
                    global counter
                    counter += 1
                    server.stdin.write(json.dumps(dict(jsonrpc='2.0', id=counter, method=method, params=params)) + '\n')
                    server.stdin.flush()
                    while True:
                        line = server.stdout.readline()
                        if not line: raise RuntimeError('DotNetLab session closed')
                        response = json.loads(line)
                        if response.get('id') == counter:
                            if 'error' in response: raise RuntimeError(response)
                            return response['result']
                rpc('initialize', dict(protocolVersion='2024-11-05', capabilities={}, clientInfo=dict(name='rtree-optimization', version='1')))
                server.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n'); server.stdin.flush()
                manifest = rpc('tools/list', {})
                (output / 'tool-manifest.json').write_text(json.dumps(manifest, indent=2))
                names = {t['name'].replace('_', '.'): t['name'] for t in manifest['tools']}
                print('DotNetLab tools:', list(names), flush=True)
                def call(name, request, filename=None):
                    result = rpc('tools/call', dict(name=names[name], arguments={'request': request}))
                    if result.get('isError'): raise RuntimeError(result)
                    payload = json.loads(next(c['text'] for c in result['content'] if c['type'] == 'text'))
                    if filename: (output / filename).write_text(json.dumps(payload, indent=2))
                    if payload['status'] not in ('ok', 'accepted'): raise RuntimeError(payload)
                    return payload['data']
                targets = call('lab.discover', {'action':'targets','limit':100})
                identity = next(t for t in targets['rows'] if t['process_id'] == target.pid)
                (output / 'identity.json').write_text(json.dumps(identity, indent=2))
                call('lab.discover', {'action':'capabilities','target_id':identity['target_id']}, 'capabilities.json')
                call('lab.discover', {'action':'compatibility','target_id':identity['target_id']}, 'compatibility.json')
                operation = call('lab.run', dict(action='start_capture', target_id=identity['target_id'], expected_target_epoch=identity['epoch'],
                    profile='cpu-diagnostic', duration_seconds=5, grant_id=grant['id'], idempotency_key=identity_tag + '-' + phase + '-cpu-v1'), 'start.json')
                def completed(operation):
                    deadline = time.monotonic() + 60
                    while operation['state'] not in ('completed','failed','cancelled'):
                        if time.monotonic() > deadline: raise RuntimeError('Operation deadline exceeded')
                        time.sleep(0.5)
                        operation = call('lab.run', dict(action='status',operation_id=operation['id']))
                    if operation['state'] != 'completed': raise RuntimeError(operation)
                    return operation
                operation = completed(operation)
                (output / 'capture-operation.json').write_text(json.dumps(operation, indent=2))
                capture_id = operation['result_id']
                capture_record = call('lab.inspect', {'action':'record','id':capture_id}, 'capture-record.json')
                capture = json.loads(capture_record['json'])
                trace_hash = capture['artifact_id'][4:]
                trace = next(catalog.rglob(trace_hash))
                if not trace.resolve().is_relative_to(catalog.resolve()) or hashlib.sha256(trace.read_bytes()).hexdigest() != trace_hash:
                    raise RuntimeError('Capture artifact provenance failed')
                shutil.copyfile(trace, output / 'capture.nettrace')
                analysis = call('lab.run', dict(action='analyze_stacks', capture_id=capture_id, idempotency_key=identity_tag + '-' + phase + '-stacks-v1'))
                analysis = completed(analysis)
                (output / 'analysis-operation.json').write_text(json.dumps(analysis, indent=2))
                call('lab.query', dict(view='hotspots', result_id=analysis['result_id'], ranking='self', limit=15), 'hotspots.json')
                hypothesis = call('lab.experiment', dict(action='create_hypothesis', mechanism='Leaf entries carry unused child references and contained-subtree collection performs per-value List.Add.',
                    prediction='Separate leaf bounds/values and bulk-copy contained leaves to reduce query work without changing mutable semantics.', evidence_ids=[capture_id,analysis['result_id']]), 'hypothesis.json')
                print(phase, 'capture', capture_id, 'analysis', analysis['result_id'], flush=True)
            finally:
                if server is not None:
                    server.stdin.close()
                    try: server.wait(timeout=10)
                    except subprocess.TimeoutExpired: server.terminate(); server.wait(timeout=10)
                if target.poll() is None: target.terminate()
                target.wait(timeout=10)
                jit = output / 'jit.txt'
                if jit.exists(): jit.write_text('\n'.join(line.rstrip() for line in jit.read_text(encoding='utf8').splitlines())+'\n',encoding='utf8')
finally:
    kernel.ReleaseMutex(mutex)
    kernel.CloseHandle(mutex)
