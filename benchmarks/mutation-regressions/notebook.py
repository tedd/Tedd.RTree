"""Retain synchronous DotNetLab notebook dispositions after the owned capture controller exits."""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root, destination, state = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
assert root == Path('D:/Workspaces/AI/rtree-mutation-regressions').resolve()
assert state in ('supported','inconclusive','not_supported')
host = Path('D:/Workspaces/AI/dotnetlab-installations/9c23369/Tedd.DotNetLab.Host.dll')
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateMutexW.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
kernel.ReleaseMutex.argtypes=[ctypes.c_void_p]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
mutex=kernel.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
assert kernel.WaitForSingleObject(mutex,1000) in (0,0x80), 'Performance host busy'
records=[]
def call(tool,request):
    p=subprocess.run(['dotnet',str(host),'call',str(root/'lab'),tool],input=json.dumps(request),capture_output=True,text=True)
    if p.returncode:
        records.append(dict(tool=tool,request=request,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        raise RuntimeError(f'{tool} failed: {p.returncode}')
    response=json.loads(p.stdout)
    assert response['status']=='ok',response
    records.append(dict(tool=tool,request=request,response=response))
    return response['data']
try:
    for folder, disposition in (('profiles-baseline','not_supported'),('profiles-final',state),('profiles-release',state)):
        for path in sorted((destination/folder).glob('*/hypothesis.json')):
            hypothesis=json.loads(path.read_text())['data']
            record=call('lab.inspect',dict(action='record',id=hypothesis['id']))
            call('lab.experiment',dict(action='revise_hypothesis',id=hypothesis['id'],expected_revision=record['revision'],
                mechanism=hypothesis['mechanism'],prediction=hypothesis['prediction'],state=disposition,evidence_ids=hypothesis['evidence_ids']))
            for name in ('capture-operation','analysis-operation'):
                operation=json.loads((path.parent/(name+'.json')).read_text())
                retained=call('lab.inspect',dict(action='record',id=operation['result_id']))
                (path.parent/(name+'-retained-record.json')).write_text(json.dumps(retained,indent=2))
    identity=hashlib.sha256((root/'candidate-worker/Tedd.RTree.dll').read_bytes()).hexdigest()
    # Candidate creation is optional notebook metadata, not qualified confirmation.
    call('lab.experiment',dict(action='create_candidate',name='Exact cached metrics and selectively inlined bounds unions',build_identity=identity,components=['A03 metric reuse','A09 exact bounded-integer specialization','C18 private union constructor inlining']))
finally:
    (destination/'notebook-dispositions.json').write_text(json.dumps(records,indent=2))
    kernel.ReleaseMutex(mutex);kernel.CloseHandle(mutex)
