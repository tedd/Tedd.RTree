"""Build a reviewable specialization proposal without modifying production source."""
import sys
sys.dont_write_bytecode=True
import difflib, json, shutil
import research as r

def write_patch(root):
    patch=[]
    for p in sorted(root.glob('*.cs')):
        control=r.REPO/'src/Tedd.RTree'/p.name
        before=control.read_bytes().decode('utf8') if control.exists() else ''
        after=p.read_text()
        if '\r\n' in before:after=after.replace('\n','\r\n')
        patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/src/Tedd.RTree/'+p.name if control.exists() else '/dev/null',tofile='b/src/Tedd.RTree/'+p.name))
    (r.REPORT/'specialization.patch').write_bytes(''.join(patch).encode('utf8'))

def prepare(selected):
    if selected not in ('KeyPackedRTree','RadixPackedRTree'):raise ValueError(selected)
    root=r.ROOT/'proposal-source/src/Tedd.RTree';root.mkdir(parents=True,exist_ok=True)
    for p in (r.REPO/'src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs','.csproj'):shutil.copyfile(p,root/p.name)
    baseline={p.name:r.digest(p) for p in (r.REPO/'src/Tedd.RTree').glob('*.cs')}
    shutil.copyfile(r.REPORT/'IReadOnlySpatialIndex.cs',root/'IReadOnlySpatialIndex.cs')
    shutil.copyfile(r.ROOT/'library-source/src/Tedd.RTree/HilbertOrder.cs',root/'HilbertOrder.cs')
    for suffix,kind,bounds in (('', 'RTree<T>', 'Rectangle'),('2D.Generic','RTree2D<TCoordinate, T>','Rectangle2D<TCoordinate>'),('3D.Generic','RTree3D<TCoordinate, T>','Box<TCoordinate>')):
        ending='.'+suffix if suffix else ''
        for prefix in ('','Snapshot','Concurrent'):
            p=root/f'{prefix}RTree{ending}.cs'
            if suffix:p=root/f'{prefix}RTree{suffix}.cs'
            t=p.read_text();decl='public sealed class '+prefix+kind
            interface=('IMutableSpatialIndex' if not prefix else 'IReadOnlySpatialIndex')+f'<{bounds}, T>'
            if prefix=='Concurrent':t=t.replace(decl+' : IDisposable',decl+' : IDisposable, '+interface,1)
            else:t=t.replace(decl,decl+' : '+interface,1)
            p.write_text(t,encoding='utf8',newline='\n')
    t=(r.REPORT/f'{selected}.cs').read_text().replace(selected,'PackedRTree')
    t=t.replace('/// <summary>Research prototype: immutable flat 2D index with owned storage.</summary>', '''/// <summary>An immutable, packed two-dimensional spatial index with double coordinates.</summary>
/// <remarks>Construction copies entries into owned storage. Concurrent searches require separate result lists.
/// An optional workspace is exclusive scratch storage during construction and is not retained.</remarks>
/// <typeparam name="T">The indexed value type.</typeparam>''')
    t=t.replace('    public int Count { get; }','    /// <summary>Gets the number of indexed entries, including duplicates.</summary>\n    public int Count { get; }')
    t=t.replace('    public PackedRTree(','''    /// <summary>Builds an immutable index from the supplied entries.</summary>
    /// <param name="items">Entries to copy; duplicates are retained.</param>
    /// <param name="maxEntries">Maximum entries per node, from 4 through 128.</param>
    /// <param name="workspace">Optional exclusive scratch space, reusable after construction.</param>
    public PackedRTree(''')
    t=t.replace('        bool partial = false, BulkLoadWorkspace? workspace = null)','        BulkLoadWorkspace? workspace = null)')
    t=t.replace('if (!partial && Count <','if (Count <')
    t=t.replace('            if (partial) PartialOrder.Sort(keys, order, scratch, _capacity);\n            else HilbertOrder.SortIndices(keys, order, scratch);','            HilbertOrder.SortIndices(keys, order, scratch);')
    for signature in ('public int Search(Rectangle bounds, List<T> results)','public List<T> Search(Rectangle bounds)','public long SearchBatch('):
        t=t.replace('    '+signature,'    /// <inheritdoc/>\n    '+signature,1)
    (root/'PackedRTree.cs').write_text(t,encoding='utf8',newline='\n')
    assert 'partial' not in t
    write_patch(root)
    (r.REPORT/'selection.json').write_text(json.dumps(dict(selected=selected,capacity=16,baseline=baseline,source={p.name:r.digest(p) for p in root.glob('*.cs')}),indent=2))
    r.run([r.DOTNET,'build',root/'Tedd.RTree.csproj','-c','Release','--artifacts-path',r.ROOT/'proposal-artifacts','-o',r.ROOT/'proposal-library','-p:UseSharedCompilation=false'],r.ROOT/'proposal-build.txt')
    # Use an independent caller, same read interface for mutable and immutable variants.
    t=(r.REPO/'benchmarks/specialization/Worker.cs').read_text()
    first=t.index('    if (mode == "mutable")');last=t.index('\n}',first)
    t=t[:first]+'''    if (mode == "mutable") { var t = new RTree<int>(); t.BulkLoad(entries); return t; }
    if (mode == "packed") return new PackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");'''+t[last:]
    t=t.replace('ResearchChecks.Run(); ExtraChecks.Run();','ProposalChecks.Run();')
    (r.ROOT/'ProposalWorker.cs').write_text(t,encoding='utf8',newline='\n')
    project=r.ROOT/'ProposalBench.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><AssemblyName>Bench</AssemblyName><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{r.ROOT}/ProposalWorker.cs"/><Compile Include="{r.REPORT}/ProposalChecks.cs"/><Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/proposal-library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''')
    project.write_text(project.read_text().replace('<Nullable>','<AssemblySearchPaths>{HintPathFromItem};{RawFileName}</AssemblySearchPaths><Nullable>',1))
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'proposal-caller-artifacts','-o',r.ROOT/'proposal-caller','-p:UseSharedCompilation=false'],r.ROOT/'proposal-caller-build-fixed.txt')
    assert r.digest(r.ROOT/'proposal-caller/Tedd.RTree.dll')==r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    # Full pre-existing suite plus independent proposal/contract checks.
    main=(r.REPO/'tests/Tedd.RTree.Tests/Program.cs').read_text().replace('using Tedd.RTree;','using Tedd.RTree;\nProposalChecks.Run();',1)
    (r.ROOT/'ProposalTestMain.cs').write_text(main,encoding='utf8')
    project=r.ROOT/'ProposalTests.csproj'
    project.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="{r.REPO}/tests/Tedd.RTree.Tests/*.cs" Exclude="{r.REPO}/tests/Tedd.RTree.Tests/Program.cs"/><Compile Include="{r.ROOT}/ProposalTestMain.cs"/><Compile Include="{r.REPORT}/ProposalChecks.cs"/><Reference Include="Tedd.RTree"><HintPath>{r.ROOT}/proposal-library/Tedd.RTree.dll</HintPath></Reference></ItemGroup></Project>''')
    project.write_text(project.read_text().replace('<Nullable>','<AssemblySearchPaths>{HintPathFromItem};{RawFileName}</AssemblySearchPaths><Nullable>',1))
    r.run([r.DOTNET,'build',project,'-c','Release','--artifacts-path',r.ROOT/'proposal-test-artifacts','-o',r.ROOT/'proposal-tests','-p:UseSharedCompilation=false'],r.ROOT/'proposal-tests-build.txt')
    assert r.digest(r.ROOT/'proposal-tests/Tedd.RTree.dll')==r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    for scalar in (False,True):
        env=dict(r.ENV)
        if scalar:env['DOTNET_EnableHWIntrinsic']='0'
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'proposal-tests/ProposalTests.dll'],r.REPORT/f'proposal-tests-{scalar}.txt',env=env)
    for mode in ('mutable','packed'):
        env=dict(r.ENV,DOTNET_JitDisasm='*Search* *Sort* *.ctor*',DOTNET_JitDisasmAssemblies='Tedd.RTree',DOTNET_JitStdOutFile=str(r.REPORT/f'proposal-{mode}-jit.txt'))
        r.run([r.DOTNET,'exec','--fx-version','10.0.13',r.ROOT/'proposal-caller/Bench.dll',r.ROOT/'retained/fixture-10000-uniform.txt',mode,'codegen'],r.ROOT/f'proposal-{mode}-codegen.txt',env=env)
    print('Frozen proposal and all hardware/fallback tests pass.',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='patch':write_patch(r.ROOT/'proposal-source/src/Tedd.RTree');sys.exit(0)
    import ctypes
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    m=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(m,1000) not in (0,0x80):raise RuntimeError('Host busy')
    try:prepare(sys.argv[1])
    finally:k.ReleaseMutex(m);k.CloseHandle(m)
