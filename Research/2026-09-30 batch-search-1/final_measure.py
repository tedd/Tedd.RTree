"""Final acceptance; invoke with the shared performance lock."""
import pathlib
import subprocess
import os
import datetime
import json
RUN=pathlib.Path(__file__).resolve().parent
ROOT=RUN.parents[1]
RAW=RUN/'raw'
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(command,name,env=None):
    print('Executing:',command,flush=True)
    with (RAW/(name+'.txt')).open('w',encoding='utf-8') as out:
        result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env=env)
    if result.returncode:
        print((RAW/(name+'.txt')).read_text(),flush=True)
        raise SystemExit(result.returncode)
run(['dotnet','build','Tedd.RTree.sln','-c','Release'],'final-solution-build')
run(['dotnet','run','--project','tests/Tedd.RTree.Tests','-c','Release','--no-build'],'final-tests')
run(['dotnet','build',str(RUN/'Investigation.csproj'),'-c','Release'],'final-investigation-build')
dll=str(RUN/'bin/Release/net10.0/Investigation.dll')
run(['dotnet',dll,'--focused-screen',str(RAW/'focused-screen.csv')],'focused-screen')
run(['dotnet',dll,'--generic-screen',str(RAW/'generic-final-screen.csv')],'generic-final-screen')
env=dict(os.environ,DOTNET_JitDisasm='*Search*',DOTNET_JitDisasmAssemblies='Investigation',DOTNET_JitDisasmDiffable='1')
run(['dotnet',dll,'--generic-screen',str(RAW/'generic-diagnostic-screen.csv')],'generic-tiered-search',env)
(RAW/'final-lock-window.json').write_text(json.dumps({'startUtc':start,'endUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'lock':str(pathlib.Path.home()/'.codex/locks/performance-measurement.lock')},indent=2))
