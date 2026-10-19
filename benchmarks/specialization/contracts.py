"""Split and validate the additive contracts independently of experimental algorithms."""
import sys
sys.dont_write_bytecode=True
import re,shutil,json
import research as r

def main():
    sections=re.split(r'(?=^--- (?:a/|/dev/null))',(r.REPORT/'specialization.patch').read_bytes().decode('utf8'),flags=re.M)
    contracts=[];packed=[]
    for section in sections:
        if not section:continue
        name=next(x[4:].rsplit('/',1)[-1] for x in section.splitlines() if x.startswith('+++ '))
        (packed if name in ('PackedRTree.cs','HilbertOrder.cs') else contracts).append(section)
    for name,parts in (('contracts-only.patch',contracts),('packed-index.patch',packed)):
        (r.REPORT/name).write_bytes(''.join(parts).encode('utf8'))
    source=r.ROOT/'contracts-source/src/Tedd.RTree';source.mkdir(parents=True,exist_ok=False)
    for p in (r.REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,source/p.name)
    for p in (r.ROOT/'proposal-source/src/Tedd.RTree').glob('*RTree*.cs'):
        if p.name!='PackedRTree.cs':shutil.copyfile(p,source/p.name)
    shutil.copyfile(r.REPORT/'IReadOnlySpatialIndex.cs',source/'IReadOnlySpatialIndex.cs')
    env=dict(r.ENV,DOTNET_CLI_HOME=str(r.ROOT/'cli-home'),DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='1')
    r.run([r.DOTNET,'build',source/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'contracts-artifacts','-o',r.ROOT/'contracts-library','-p:UseSharedCompilation=false'],r.ROOT/'contracts-build.txt',env=env)
    # Extract only the existing-types contract oracle; no experimental index/helper dependency.
    t=(r.REPORT/'ProposalChecks.cs').read_text();start=t.index('    private static void ReadContracts()');end=t.index('    private sealed class IndexedOnly',start)
    check=t[start:end].replace('private static void ReadContracts()','internal static void Run()',1)
    check=re.sub(r'        if\(\(object\)new PackedRTree<int>.*?throw new Exception\("Immutable tree advertises mutation"\);\n','',check,flags=re.S)
    (r.ROOT/'ContractChecks.cs').write_text('using Tedd.RTree;\ninternal static class ContractChecks\n{\n'+check+'}\n',encoding='utf8',newline='\n')
    main=(r.REPO/'tests/Tedd.RTree.Tests/Program.cs').read_text().replace('using Tedd.RTree;','using Tedd.RTree;\nContractChecks.Run();',1)
    (r.ROOT/'ContractTestMain.cs').write_text(main,encoding='utf8',newline='\n')
    project=r.ROOT/'ContractTests.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><AssemblySearchPaths>{{HintPathFromItem}};{{RawFileName}}</AssemblySearchPaths><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{r.REPO}/tests/Tedd.RTree.Tests/*.cs" Exclude="{r.REPO}/tests/Tedd.RTree.Tests/Program.cs"/><Compile Include="{r.ROOT}/ContractChecks.cs"/><Compile Include="{r.ROOT}/ContractTestMain.cs"/><Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/contracts-library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''')
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'contracts-test-artifacts','-o',r.ROOT/'contracts-tests','-p:UseSharedCompilation=false'],r.ROOT/'contracts-tests-build.txt',env=env)
    assert r.digest(r.ROOT/'contracts-library/Tedd.RTree.dll')==r.digest(r.ROOT/'contracts-tests/Tedd.RTree.dll')
    for scalar in (False,True):
        target_env=dict(env)
        if scalar:target_env['DOTNET_EnableHWIntrinsic']='0'
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'contracts-tests/ContractTests.dll'],r.REPORT/f'contracts-tests-{scalar}.txt',env=target_env)
    record=dict(source={p.name:r.digest(p) for p in source.glob('*.cs')},library=r.digest(r.ROOT/'contracts-library/Tedd.RTree.dll'),tests=r.digest(r.ROOT/'contracts-tests/ContractTests.dll'),new_algorithms=False,all_nine_read_contracts=True,three_mutation_contracts=True)
    (r.REPORT/'contracts-validation.json').write_text(json.dumps(record,indent=2))
    print('Contracts-only build, all nine interface checks and full hardware/fallback suites pass.',flush=True)

if __name__=='__main__':
    import ctypes
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Host busy')
    try:main()
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)
