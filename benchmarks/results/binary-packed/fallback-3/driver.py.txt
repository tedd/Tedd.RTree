"""Inspected, in-memory external .NET experiment. No database/service effects."""
import sys
sys.dont_write_bytecode = True
import csv, ctypes, hashlib, json, os, random, shutil, statistics, subprocess, time, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path('D:/Workspaces/AI/rtree-binary-20261019')
REPORT = REPO / 'Research/2026-10-19-binary-packed'
EVIDENCE = REPO / 'benchmarks/results/binary-packed'
DOTNET = Path('C:/Program Files/dotnet/dotnet.exe')
ENV = dict(os.environ, TEMP=str(ROOT), TMP=str(ROOT), DOTNET_TieredCompilation='0',
           DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_CLI_HOME=str(ROOT/'cli-home'))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def atomic_text(path,text):
    path=Path(path);journal=ROOT/'write-journal';journal.mkdir(exist_ok=True)
    staged=journal/(hashlib.sha256(str(path).encode()).hexdigest()+'.txt')
    staged.write_text(text,encoding='utf8')
    for attempt in range(3):
        try:os.replace(staged,path);return
        except OSError:
            if attempt==2:raise
            time.sleep(.05)

def atomic_json(path,value):atomic_text(path,json.dumps(value,indent=2))

def run(cmd, log, env=None, timeout=300):
    p = subprocess.Popen(list(map(str, cmd)), cwd=ROOT, env=env or ENV,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    with (ROOT/'launch-journal.jsonl').open('a',encoding='utf8') as journal:
        journal.write(json.dumps(dict(pid=p.pid,started_ns=time.time_ns(),command=list(map(str,cmd)),log=str(log)))+'\n')
    try: out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait(); raise
    atomic_text(log,out+'\nSTDERR:\n'+err)
    if p.returncode: raise RuntimeError((cmd, p.returncode, out[-4000:], err[-2000:]))
    return out, err, p.pid

def restore():
    old = REPO/'Research/2026-10-19-specialization/reproduction.zip'
    manifest = json.loads(old.with_suffix('.manifest.json').read_text())
    assert sha(old) == manifest['archive_sha256']
    with zipfile.ZipFile(old) as z:
        for name in z.namelist():
            if name.startswith('proposal-source/') or name.startswith('retained/'):
                if name.endswith('/'): continue
                data = z.read(name)
                assert hashlib.sha256(data).hexdigest() == manifest['files'][name]['sha256']
                dest = ROOT/name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)

def generate():
    source = ROOT/'source'; source.mkdir(exist_ok=True)
    for p in (ROOT/'proposal-source/src/Tedd.RTree').iterdir():
        if p.suffix in ('.cs', '.csproj'): shutil.copyfile(p, source/p.name)
    baseline = (source/'PackedRTree.cs').read_text()
    (source/'ControlPackedRTree.cs').write_text(baseline.replace('PackedRTree', 'ControlPackedRTree'))
    (source/'PackedRTree.cs').unlink()
    shutil.copyfile(REPORT/'BinaryOrder.cs', source/'BinaryOrder.cs')
    start = baseline.index('        if (Count < 2048)')
    end = baseline.index('        Span<int> starts', start)
    binary = baseline[:start]+'        BinaryOrder.Sort(keys, order, _capacity);\n'+baseline[end:]
    (source/'BinaryPackedRTree.cs').write_text(binary.replace('PackedRTree','BinaryPackedRTree'))
    # Ownership intervention: retain normalization/search; replace sort+gather with owned swaps.
    owned = baseline
    begin = owned.index('        Span<int> starts')
    finish = owned.index('        for (int level = 1;', begin)
    hierarchy = owned[begin:finish]
    gather = hierarchy.index('        for (int i = 0; i < Count; i++)')
    hierarchy = hierarchy[:gather]+'''        for (int i = 0; i < Count; i++)
        {
            _boxes[i] = source[i].Bounds;
            _values[i] = source[i].Item;
        }
'''
    hierarchy = hierarchy.replace('_boxes = new Rectangle[total]', '_boxes = GC.AllocateUninitializedArray<Rectangle>(total)')
    owned = owned[:begin]+owned[finish:]
    start = owned.index('        if (Count < 2048)')
    end = owned.index('        for (int level = 1;', start)
    owned = owned[:start]+'        BinaryOrder.SortOwned(keys, _boxes, _values, Count, _capacity);\n'+owned[end:]
    owned = owned.replace('        Span<int> order = workspace is null ? new int[Count] : workspace.Order.AsSpan(0, Count);\n','')
    owned = owned.replace('workspace is null ? new uint[Count]', 'workspace is null ? GC.AllocateUninitializedArray<uint>(Count)')
    owned = owned.replace('        Rectangle extent = source[0].Bounds;', hierarchy+'        Rectangle extent = source[0].Bounds;')
    owned = owned.replace('source[index].Bounds', '_boxes[index]').replace('source[i].Bounds;', '_boxes[i];')
    # The latter replacement also touches the initial copy: restore that assignment.
    owned = owned.replace('_boxes[i] = _boxes[i];', '_boxes[i] = source[i].Bounds;')
    owned = owned.replace('            order[index] = index;\n','').replace('            order[i] = i;\n','')
    (source/'OwnedPackedRTree.cs').write_text(owned.replace('PackedRTree','OwnedPackedRTree'))
    begin = owned.index('        Span<uint> xs =')
    finish = owned.index('        BinaryOrder.SortOwned', begin)
    normalization = '''        for (int i = 0; i < Count; i++)
        {
            Rectangle b = _boxes[i];
            double x = b.MinX * 0.25 + b.MaxX * 0.25 - minX;
            double y = b.MinY * 0.25 + b.MaxY * 0.25 - minY;
            uint ix = width > 0 ? (uint)Math.Clamp(finiteX ? x * scaleX : x / width * 65535, 0, 65535) : 0;
            uint iy = height > 0 ? (uint)Math.Clamp(finiteY ? y * scaleY : y / height * 65535, 0, 65535) : 0;
            keys[i] = ix | (iy << 16);
        }
        int vectorCount = Vector256.IsHardwareAccelerated ? Count & ~7 : 0;
        for (int i = 0; i < vectorCount; i += 8)
        {
            var xy = Vector256.LoadUnsafe(ref System.Runtime.InteropServices.MemoryMarshal.GetReference(keys), (nuint)i);
            var key = HilbertOrder.Encode(xy & Vector256.Create(65535u), xy >>> 16);
            key.StoreUnsafe(ref System.Runtime.InteropServices.MemoryMarshal.GetReference(keys), (nuint)i);
        }
        for (int i = vectorCount; i < Count; i++)
        {
            uint xy = keys[i];
            keys[i] = HilbertOrder.Encode(xy & 65535, xy >> 16);
        }
'''
    split = owned[:begin]+normalization+owned[finish:]
    (source/'SplitPackedRTree.cs').write_text(split.replace('PackedRTree','SplitPackedRTree'))
    for p in source.glob('*PackedRTree.cs'): shutil.copyfile(p, REPORT/p.name)
    worker = (REPO/'benchmarks/specialization/Worker.cs').read_text()
    start = worker.index('    if (mode == "mutable")'); end = worker.index('\n}', start)
    worker = worker[:start]+'''    if (mode == "mutable") { var t = new RTree<int>(); t.BulkLoad(entries); return t; }
    if (mode == "control") return new ControlPackedRTree<int>(entries);
    if (mode == "binary") return new BinaryPackedRTree<int>(entries);
    if (mode == "owned") return new OwnedPackedRTree<int>(entries);
    if (mode == "split") return new SplitPackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");'''+worker[end:]
    worker = worker.replace('ResearchChecks.Run(); ExtraChecks.Run();','BinaryChecks.Run();')
    (ROOT/'Worker.cs').write_text(worker)

def project(path, compile_items, references='', assembly='Bench'):
    path.write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><AssemblyName>{assembly}</AssemblyName><AssemblySearchPaths>{{HintPathFromItem}};{{RawFileName}}</AssemblySearchPaths><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems><AllowUnsafeBlocks>true</AllowUnsafeBlocks></PropertyGroup><ItemGroup>{''.join(f'<Compile Include="{p}"/>' for p in compile_items)}{references}</ItemGroup></Project>''')

def build(epoch='construction'):
    run([DOTNET,'build',ROOT/'source/Tedd.RTree.csproj','-c','Release','--artifacts-path',ROOT/(epoch+'-lib-artifacts'),'-o',ROOT/(epoch+'-library'),'-p:UseSharedCompilation=false'],ROOT/(epoch+'-build.txt'))
    refs=f'<Reference Include="Tedd.RTree"><HintPath>{ROOT}/{epoch}-library/Tedd.RTree.dll</HintPath></Reference>'
    items=[ROOT/'Worker.cs', REPORT/'BinaryChecks.cs']
    if (ROOT/'source/KeyEncoding.cs').exists():items.append(REPORT/'EncodingChecks.cs')
    proj=ROOT/(epoch+'.csproj'); project(proj,items,refs)
    run([DOTNET,'build',proj,'-c','Release','--artifacts-path',ROOT/(epoch+'-caller-artifacts'),'-o',ROOT/(epoch+'-caller'),'-p:UseSharedCompilation=false'],ROOT/(epoch+'-caller-build.txt'))
    assert sha(ROOT/(epoch+'-library/Tedd.RTree.dll'))==sha(ROOT/(epoch+'-caller/Tedd.RTree.dll'))

def traversal(selected):
    names={'binary':'BinaryPackedRTree','owned':'OwnedPackedRTree','split':'SplitPackedRTree','control':'ControlPackedRTree'}
    original=(ROOT/'source'/f'{names[selected]}.cs').read_text()
    method=(REPORT/'IterativeSearch.cs.txt').read_text()
    for name,contains in (('OverlapPackedRTree',False),('IterativePackedRTree',True)):
        text=original.replace(names[selected],name)
        first=text.index('    private int SearchLevel(');last=text.index('    /// <inheritdoc/>',first)
        body=method
        if contains:
            body=body.replace('                // CONTAINMENT','''                if (bounds.Contains(box))
                {
                    int valueStart = local * _spans[level];
                    results.AddRange(_values.AsSpan(valueStart, Math.Min(_spans[level], Count - valueStart)));
                    continue;
                }''')
        else:body=body.replace('                // CONTAINMENT\n','')
        text=text[:first]+body+text[last:]
        (ROOT/'source'/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    p=ROOT/'Worker.cs';text=p.read_text().replace('    throw new ArgumentException("Unknown mode");','''    if (mode == "overlap") return new OverlapPackedRTree<int>(entries);
    if (mode == "iterative") return new IterativePackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");''');p.write_text(text)
    p=REPORT/'BinaryChecks.cs';text=p.read_text().replace('        _ => throw new ArgumentException(mode)','''        "overlap" => new OverlapPackedRTree<T>(entries, capacity, workspace),
        "iterative" => new IterativePackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)''').replace('"control", "binary", "owned", "split"]','"control", "binary", "owned", "split", "overlap", "iterative"]');p.write_text(text)
    (REPORT/'traversal-selection.json').write_text(json.dumps(dict(construction=selected,source=sha(ROOT/'source'/f'{names[selected]}.cs')),indent=2))
    build('traversal');checks('traversal')

def remedies():
    source=ROOT/'source'
    for name in ('RefBinaryOrder.cs','KeyEncoding.cs'):shutil.copyfile(REPORT/name,source/name)
    baseline=(source/'ControlPackedRTree.cs').read_text()
    for name,partition,vector in (('RefPackedRTree',True,False),('VectorPackedRTree',False,True),('CombinedPackedRTree',True,True)):
        text=baseline.replace('ControlPackedRTree',name)
        if partition:text=text.replace('if (Count < 2048) keys.Sort(order);','if (Count < 2048) RefBinaryOrder.Sort(keys, order, _capacity);')
        if vector:
            start=text.index('        Span<uint> xs =');end=text.index('        if (Count < 2048)',start)
            text=text[:start]+'        KeyEncoding.Fill(source, keys, order, minX, minY, width, height, scaleX, scaleY);\n'+text[end:]
        (source/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    (source/'ExperimentAssembly.cs').write_text('using System.Runtime.CompilerServices;\n[assembly: InternalsVisibleTo("Bench")]\n')
    p=ROOT/'Worker.cs';text=p.read_text().replace('    throw new ArgumentException("Unknown mode");','''    if (mode == "ref") return new RefPackedRTree<int>(entries);
    if (mode == "vector") return new VectorPackedRTree<int>(entries);
    if (mode == "combined") return new CombinedPackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");''');p.write_text(text)
    p=REPORT/'BinaryChecks.cs';text=p.read_text().replace('        _ => throw new ArgumentException(mode)','''        "ref" => new RefPackedRTree<T>(entries, capacity, workspace),
        "vector" => new VectorPackedRTree<T>(entries, capacity, workspace),
        "combined" => new CombinedPackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)''').replace('"overlap", "iterative"]','"overlap", "iterative", "ref", "vector", "combined"]')
    text=text.replace('    internal static void Run()\n    {','    internal static void Run()\n    {\n        EncodingChecks.Run();');p.write_text(text)
    build('remedies');checks('remedies');codegen('remedies',['ref','vector','combined'])

def query_remedies():
    source=ROOT/'source';baseline=(source/'ControlPackedRTree.cs').read_text()
    shutil.copyfile(REPORT/'ResultBuffer.cs',source/'ResultBuffer.cs')
    original_start=baseline.index('    private int SearchLevel(')
    original_end=baseline.index('    /// <inheritdoc/>',original_start)
    recursive=baseline[original_start:original_end]
    workstack=(REPORT/'WorkStackSearch.cs.txt').read_text()
    for name,stack,buffer in (('StackPackedRTree',True,False),('BufferPackedRTree',False,True),('StackBufferPackedRTree',True,True)):
        text=baseline.replace('ControlPackedRTree',name)
        method=workstack if stack else recursive
        first=text.index('    private int SearchLevel(');last=text.index('    /// <inheritdoc/>',first)
        text=text[:first]+method+text[last:]
        if buffer:
            buf=method.replace('private int SearchLevel(', 'private void SearchBufferLevel(').replace('List<T> results)', 'ref ResultBuffer<T> results)')
            buf=buf.replace('        int found = 0;\n','').replace('found++;','').replace('                    found += count;\n','').replace('found += SearchLevel(', 'SearchBufferLevel(').replace('bounds, results);','bounds, ref results);').replace('        return found;\n','')
            buf=buf.replace('        int initialCount=results.Count;\n','').replace('if(depth==0)return results.Count-initialCount;','if(depth==0)return;')
            wrapper='''    private int SearchBuffered(int level, int start, int end, in Rectangle bounds, List<T> results)
    {
        var writer=new ResultBuffer<T>(results);
        try { SearchBufferLevel(level,start,end,bounds,ref writer); return writer.Appended; }
        finally { writer.Commit(); }
    }

'''
            first=text.index('    private int SearchLevel(')
            text=text[:first]+wrapper+buf+text[first:]
            text=text.replace('        return SearchLevel(level, _starts[level], _boxes.Length, bounds, results);','''        if(!System.Runtime.CompilerServices.RuntimeHelpers.IsReferenceOrContainsReferences<T>())
            return SearchBuffered(level,_starts[level],_boxes.Length,bounds,results);
        return SearchLevel(level, _starts[level], _boxes.Length, bounds, results);''')
        (source/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    for name,parent in (('PredicatePackedRTree','ControlPackedRTree'),('PredicateBufferPackedRTree','BufferPackedRTree')):
        text=(source/f'{parent}.cs').read_text().replace(parent,name)
        for expression in ('_extent','boxes[j]','box','_boxes[i]'):
            text=text.replace(expression+'.Intersects(bounds)',f'Overlaps({expression},bounds)')
        helper='''    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Overlaps(in Rectangle box,in Rectangle query) =>
        box.MaxX>=query.MinX && box.MaxY>=query.MinY && box.MinX<=query.MaxX && box.MinY<=query.MaxY;

'''
        where=text.index('    /// <inheritdoc/>')
        text=text[:where]+helper+text[where:]
        (source/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    p=ROOT/'Worker.cs';text=p.read_text().replace('    throw new ArgumentException("Unknown mode");','''    if (mode == "stack") return new StackPackedRTree<int>(entries);
    if (mode == "buffer") return new BufferPackedRTree<int>(entries);
    if (mode == "stack-buffer") return new StackBufferPackedRTree<int>(entries);
    if (mode == "predicate") return new PredicatePackedRTree<int>(entries);
    if (mode == "predicate-buffer") return new PredicateBufferPackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");''');p.write_text(text)
    p=REPORT/'BinaryChecks.cs';text=p.read_text().replace('        _ => throw new ArgumentException(mode)','''        "stack" => new StackPackedRTree<T>(entries, capacity, workspace),
        "buffer" => new BufferPackedRTree<T>(entries, capacity, workspace),
        "stack-buffer" => new StackBufferPackedRTree<T>(entries, capacity, workspace),
        "predicate" => new PredicatePackedRTree<T>(entries, capacity, workspace),
        "predicate-buffer" => new PredicateBufferPackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)''').replace('"ref", "vector", "combined"]','"ref", "vector", "combined", "stack", "buffer", "stack-buffer"]')
    text=text.replace('"stack", "buffer", "stack-buffer"]','"stack", "buffer", "stack-buffer", "predicate", "predicate-buffer"]');p.write_text(text)
    build('query-remedies');checks('query-remedies');codegen('query-remedies',['control','stack','buffer','stack-buffer','predicate','predicate-buffer'])

def construction_passes():
    source=ROOT/'source';baseline=(source/'VectorPackedRTree.cs').read_text()
    shutil.copyfile(REPORT/'BoundsReduction.cs',source/'BoundsReduction.cs')
    for name,reduction,packed in (('ReducePackedRTree',True,False),('WidePackedRTree',False,True),('WideReducePackedRTree',True,True)):
        text=baseline.replace('VectorPackedRTree',name)
        if reduction:
            text=text.replace('''        Rectangle extent = source[0].Bounds;
        for (int i = 1; i < source.Length; i++) extent = Rectangle.Union(extent, source[i].Bounds);''','''        Rectangle extent = BoundsReduction.Entries(source);''')
            text=text.replace('''                Rectangle bounds = _boxes[first];
                for (int i = first + 1; i < end; i++) bounds = Rectangle.Union(bounds, _boxes[i]);''','''                Rectangle bounds = BoundsReduction.Boxes(_boxes.AsSpan(first,end-first));''')
        if packed:
            text=text.replace('workspace?.EnsureCapacity(Count);','workspace?.EnsureCapacity(Count < 2048 ? Count * 2 : Count);')
            start=text.index('        Span<int> order =');end=text.index('        Rectangle extent',start)
            text=text[:start]+'''        Span<ulong> packed = Count < 2048
            ? workspace is null ? new ulong[Count] : System.Runtime.InteropServices.MemoryMarshal.Cast<int,ulong>(workspace.HilbertScatter(Count*2))
            : default;
        Span<int> order = Count < 2048 ? System.Runtime.InteropServices.MemoryMarshal.Cast<ulong,int>(packed).Slice(Count,Count)
            : workspace is null ? new int[Count] : workspace.Order.AsSpan(0,Count);
        Span<uint> keys = Count < 2048 ? System.Runtime.InteropServices.MemoryMarshal.Cast<ulong,uint>(packed).Slice(0,Count)
            : workspace is null ? new uint[Count] : workspace.HilbertKeys(Count);
'''+text[end:]
            text=text.replace('        if (Count < 2048) keys.Sort(order);','''        if (Count < 2048)
        {
            // Descending writes only overwrite keys at indices >= the key just read.
            for(int i=Count-1;i>=0;i--)packed[i]=((ulong)keys[i]<<32)|(uint)i;
            packed.Sort();
        }''')
            start=text.index('        for (int i = 0; i < Count; i++)',text.index('        _values = new T[Count];'))
            end=text.index('        for (int level = 1;',start)
            old=text[start:end]
            text=text[:start]+'''        if(Count<2048)
        {
            for(int i=0;i<Count;i++)
            {
                var entry=source[(int)(uint)packed[i]];
                _boxes[i]=entry.Bounds;_values[i]=entry.Item;
            }
        }
        else
        {
'''+old+'''        }
'''+text[end:]
        (source/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    p=ROOT/'Worker.cs';text=p.read_text().replace('    throw new ArgumentException("Unknown mode");','''    if (mode == "reduce") return new ReducePackedRTree<int>(entries);
    if (mode == "wide") return new WidePackedRTree<int>(entries);
    if (mode == "wide-reduce") return new WideReducePackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");''');p.write_text(text)
    p=REPORT/'BinaryChecks.cs';text=p.read_text().replace('        _ => throw new ArgumentException(mode)','''        "reduce" => new ReducePackedRTree<T>(entries, capacity, workspace),
        "wide" => new WidePackedRTree<T>(entries, capacity, workspace),
        "wide-reduce" => new WideReducePackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)''').replace('"predicate", "predicate-buffer"]','"predicate", "predicate-buffer", "reduce", "wide", "wide-reduce"]');p.write_text(text)
    build('passes');checks('passes');codegen('passes',['vector','reduce','wide','wide-reduce'])

def representation(selected):
    names={'vector':'VectorPackedRTree','reduce':'ReducePackedRTree','wide':'WidePackedRTree','wide-reduce':'WideReducePackedRTree'}
    source=ROOT/'source';baseline=(source/f'{names[selected]}.cs').read_text()
    for name,vector in (('NormalizedScalarPackedRTree',False),('NormalizedVectorPackedRTree',True)):
        text=baseline.replace(names[selected],name)
        text=text.replace('readonly Rectangle[] _boxes','readonly Vector256<double>[] _boxes').replace('new Rectangle[total]','new Vector256<double>[total]')
        text=text.replace('_boxes[i] = entry.Bounds;', '_boxes[i] = EncodeBounds(entry.Bounds);').replace('_boxes[i]=entry.Bounds;', '_boxes[i]=EncodeBounds(entry.Bounds);')
        start=text.index('        for (int level = 1;');end=text.index('    /// <inheritdoc/>',start)
        text=text[:start]+'''        for(int level=1;level<levels;level++)
        {
            int lowerStart=_starts[level-1],lowerEnd=_starts[level];
            for(int first=lowerStart,destination=_starts[level];first<lowerEnd;first+=_capacity,destination++)
            {
                int end=first+Math.Min(_capacity,lowerEnd-first);
                var b=_boxes[first];
                for(int i=first+1;i<end;i++)b=Vector256.Min(b,_boxes[i]);
                _boxes[destination]=b;
            }
        }
    }

    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static Vector256<double> EncodeBounds(in Rectangle b)=>Vector256.Create(b.MinX,b.MinY,-b.MaxX,-b.MaxY);

'''+text[end:]
        text=text.replace('        return SearchLevel(level, _starts[level], _boxes.Length, bounds, results);','''        var overlap=Vector256.Create(bounds.MaxX,bounds.MaxY,-bounds.MinX,-bounds.MinY);
        var contained=EncodeBounds(bounds);
        return SearchLevel(level,_starts[level],_boxes.Length,overlap,contained,results);''')
        text=text.replace('int end, in Rectangle bounds, List<T> results)','int end, in Vector256<double> overlap, in Vector256<double> contained, List<T> results)')
        text=text.replace('ReadOnlySpan<Rectangle> boxes','ReadOnlySpan<Vector256<double>> boxes').replace('ref readonly Rectangle box','ref readonly Vector256<double> box')
        text=text.replace('boxes[j].Intersects(bounds)','Overlaps(boxes[j],overlap)').replace('box.Intersects(bounds)','Overlaps(box,overlap)').replace('bounds.Contains(box)','Contains(box,contained)')
        text=text.replace('lowerEnd - first), bounds, results);','lowerEnd - first), overlap, contained, results);')
        if vector:
            helpers='''    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Overlaps(in Vector256<double> b,in Vector256<double> q)=>Vector256.LessThanOrEqualAll(b,q);
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Contains(in Vector256<double> b,in Vector256<double> q)=>Vector256.GreaterThanOrEqualAll(b,q);

'''
        else:
            helpers='''    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Overlaps(in Vector256<double> b,in Vector256<double> q)=>b.GetElement(0)<=q.GetElement(0)&&b.GetElement(2)<=q.GetElement(2)&&b.GetElement(1)<=q.GetElement(1)&&b.GetElement(3)<=q.GetElement(3);
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Contains(in Vector256<double> b,in Vector256<double> q)=>b.GetElement(0)>=q.GetElement(0)&&b.GetElement(1)>=q.GetElement(1)&&b.GetElement(2)>=q.GetElement(2)&&b.GetElement(3)>=q.GetElement(3);

'''
        where=text.index('    /// <inheritdoc/>');text=text[:where]+helpers+text[where:]
        (source/f'{name}.cs').write_text(text);(REPORT/f'{name}.cs').write_text(text)
    p=ROOT/'Worker.cs';text=p.read_text().replace('    throw new ArgumentException("Unknown mode");','''    if (mode == "normalized-scalar") return new NormalizedScalarPackedRTree<int>(entries);
    if (mode == "normalized-vector") return new NormalizedVectorPackedRTree<int>(entries);
    throw new ArgumentException("Unknown mode");''');p.write_text(text)
    p=REPORT/'BinaryChecks.cs';text=p.read_text().replace('        _ => throw new ArgumentException(mode)','''        "normalized-scalar" => new NormalizedScalarPackedRTree<T>(entries, capacity, workspace),
        "normalized-vector" => new NormalizedVectorPackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)''').replace('"reduce", "wide", "wide-reduce"]','"reduce", "wide", "wide-reduce", "normalized-scalar", "normalized-vector"]');p.write_text(text)
    atomic_json(REPORT/'representation-selection.json',dict(selected=selected,source=sha(source/f'{names[selected]}.cs')))
    build('representation');checks('representation');codegen('representation',['normalized-scalar','normalized-vector'])

def checks(epoch='construction', full=False):
    for scalar in (False, True):
        env=dict(ENV)
        if scalar: env['DOTNET_EnableHWIntrinsic']='0'
        run([DOTNET,'exec','--fx-version','10.0.13',ROOT/(epoch+'-caller/Bench.dll'),ROOT/'retained/fixture-1000-uniform.txt','split','validate'],REPORT/(epoch+f'-checks-{scalar}.txt'),env)
    if full:
        proj=ROOT/'Tests.csproj'
        refs=f'<Reference Include="Tedd.RTree"><HintPath>{ROOT}/{epoch}-library/Tedd.RTree.dll</HintPath></Reference>'
        project(proj,list((REPO/'tests/Tedd.RTree.Tests').glob('*.cs')),refs,'Tests')
        run([DOTNET,'build',proj,'-c','Release','--artifacts-path',ROOT/'test-artifacts','-o',ROOT/'tests','-p:UseSharedCompilation=false'],ROOT/'tests-build.txt')
        for scalar in (False,True):
            env=dict(ENV)
            if scalar:env['DOTNET_EnableHWIntrinsic']='0'
            run([DOTNET,'exec','--fx-version','10.0.13',ROOT/'tests/Tests.dll'],REPORT/f'original-tests-{scalar}.txt',env)

def summarize(dest):
    samples=json.loads((dest/'samples.json').read_text()); result=[]
    for n,d,m in sorted({(v['size'],v['distribution'],v['mode']) for v in samples}):
        rs=[v for v in samples if (v['size'],v['distribution'],v['mode'])==(n,d,m)]
        for op in ('build','queries','query0','query1','query2','query3'):
            if op=='queries':
                values=[sum(v['us'] for v in rs if v['block']==b and v['operation'].startswith('query')) for b in sorted({v['block'] for v in rs})];alloc=None
            else:
                ss=[v for v in rs if v['operation']==op]; values=[v['us'] for v in ss];aa=[v['allocated'] for v in ss];alloc=statistics.median(aa) if all(a is not None for a in aa) else None
            if values: result.append(dict(size=n,distribution=d,mode=m,operation=op,median_us=statistics.median(values),min_us=min(values),max_us=max(values),allocated=alloc))
    (dest/'summary.json').write_text(json.dumps(result,indent=2))
    for v in result:
        if v['operation'] in ('build','queries'): print(v,flush=True)

def codegen(epoch,modes,tiered=False):
    for mode in modes:
        env=dict(ENV,DOTNET_TieredCompilation='1' if tiered else '0',DOTNET_TieredPGO='1' if tiered else '0',
            DOTNET_JitDisasm='*Search* *Partition* *.ctor* *Encode* *Fill* *Grow* *Commit* *Entries* *Boxes*',DOTNET_JitDisasmAssemblies='Tedd.RTree',
            DOTNET_JitStdOutFile=str(REPORT/f'{epoch}-{mode}-{tiered}-jit.txt'))
        fixture='fixture-1000-uniform.txt' if mode in ('ref','combined') else 'fixture-10000-clustered.txt'
        run([DOTNET,'exec','--fx-version','10.0.13',ROOT/(epoch+'-caller/Bench.dll'),ROOT/'retained'/fixture,mode,'warm' if tiered else 'codegen'],ROOT/f'{epoch}-{mode}-{tiered}-codegen.txt',env)

def measure(phase, modes, blocks, seed, epoch='construction', tiered=False, callers=None, source_root=None, intrinsics=True):
    dest=EVIDENCE/phase;dest.mkdir(parents=True,exist_ok=False)
    jobs=[(b,n,d,m) for b in range(blocks) for n in (1000,10000,100000) for d in ('uniform','clustered') for m in modes]
    random.Random(seed).shuffle(jobs)
    runtime=Path('C:/Program Files/dotnet/shared/Microsoft.NETCore.App/10.0.13')
    protocol=dict(jobs=jobs,seed=seed,affinity=4,tiering=tiered,pgo=tiered,observer='none',runtime='10.0.13',calibration_us=100000,warmup_seconds=3 if tiered else None,
        driver=sha(__file__),source={p.name:sha(p) for p in (source_root or ROOT/'source').glob('*.cs')},caller=sha(ROOT/(epoch+'-caller/Bench.dll')),library=sha(ROOT/(epoch+'-caller/Tedd.RTree.dll')),
        fixture={p.name:sha(p) for p in (ROOT/'retained').glob('fixture-*.txt')},runtime_hashes={p:sha(runtime/p) for p in ('coreclr.dll','clrjit.dll','System.Private.CoreLib.dll')},native=sha(ROOT/'retained/native/target/release/packed-worker.exe'))
    if callers:protocol['callers']={m:{p.name:sha(p) for p in folder.glob('*.dll')} for m,folder in callers.items()}
    protocol['intrinsics']=intrinsics
    atomic_json(dest/'protocol.json',protocol);shutil.copyfile(__file__,dest/'driver.py.txt')
    samples=[];launches=[]
    for i,(b,n,d,m) in enumerate(jobs):
        fixture=ROOT/f'retained/fixture-{n}-{d}.txt'
        if m=='rust':cmd=[ROOT/'retained/native/target/release/packed-worker.exe',fixture,'static']
        else:cmd=[DOTNET,'exec','--fx-version','10.0.13',(callers[m]/'Bench.dll') if callers else ROOT/(epoch+'-caller/Bench.dll'),fixture,m]+(['warm'] if tiered else [])
        env=dict(ENV,DOTNET_TieredCompilation='1' if tiered else '0',DOTNET_TieredPGO='1' if tiered else '0',DOTNET_EnableHWIntrinsic='1' if intrinsics else '0')
        started=time.time_ns();out,err,pid=run(cmd,dest/f'{i:03d}.out',env)
        assert f'validated={128 if m=="mutable" else 64}' in err
        launches.append(dict(block=b,size=n,distribution=d,mode=m,pid=pid,started_ns=started,command=list(map(str,cmd)),validation=err.strip()))
        for row in csv.reader(out.splitlines()):
            op,us,reps,alloc=row
            samples.append(dict(block=b,size=n,distribution=d,mode=m,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        atomic_json(dest/'samples.json',samples);atomic_json(dest/'launches.json',launches)
        print(f'{i+1}/{len(jobs)} {m} {n} {d}',flush=True)
    summarize(dest)

def recover_query():
    dest=EVIDENCE/'query-remedies';protocol=json.loads((dest/'protocol.json').read_text())
    caller=ROOT/'query-remedies-caller/Bench.dll'
    assert sha(caller)==protocol['caller'] and sha(caller.parent/'Tedd.RTree.dll')==protocol['library']
    assert all(sha(ROOT/'retained'/n)==v for n,v in protocol['fixture'].items())
    assert sha(ROOT/'retained/native/target/release/packed-worker.exe')==protocol['native']
    jobs=protocol['jobs'];existing=json.loads((dest/'launches.json').read_text());samples=[];launches=[]
    logs=sorted(dest.glob('*.out'));assert len(logs)==112
    atomic_json(dest/'recovery.json',dict(reason='OSError errno 22 opening samples.json after job 112 raw log was committed',completed_logs=112,next_job=112,
        original_driver=protocol['driver'],recovery_driver=sha(__file__),missing_pid_job=111,
        policy='Retain every completed log. Do not rerun or replace completed timing observations. Resume original job order and binaries.',resumed_ns=time.time_ns()))
    shutil.copyfile(__file__,dest/'recovery-driver.py.txt')
    for i,(b,n,d,m) in enumerate(jobs):
        path=dest/f'{i:03d}.out';fixture=ROOT/f'retained/fixture-{n}-{d}.txt'
        cmd=[ROOT/'retained/native/target/release/packed-worker.exe',fixture,'static'] if m=='rust' else [DOTNET,'exec','--fx-version','10.0.13',caller,fixture,m]
        if i<112:
            text=path.read_text();out,err=text.split('\nSTDERR:\n',1)
            launch=existing[i] if i<len(existing) else dict(block=b,size=n,distribution=d,mode=m,pid=None,started_ns=None,command=list(map(str,cmd)),validation=err.strip(),identity_note='PID/start bookkeeping unavailable after summary write failure; raw stdout and validation retained')
        else:
            started=time.time_ns();out,err,pid=run(cmd,path,dict(ENV,DOTNET_TieredCompilation='0',DOTNET_TieredPGO='0'))
            launch=dict(block=b,size=n,distribution=d,mode=m,pid=pid,started_ns=started,command=list(map(str,cmd)),validation=err.strip())
        assert 'validated=64' in err
        launches.append(launch)
        rows=list(csv.reader(out.strip().splitlines()));assert len(rows)==5
        for op,us,reps,alloc in rows:
            samples.append(dict(block=b,size=n,distribution=d,mode=m,operation=op,us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        atomic_json(dest/'samples.json',samples);atomic_json(dest/'launches.json',launches)
        if i>=112:print(f'{i+1}/{len(jobs)} recovered {m} {n} {d}',flush=True)
    summarize(dest)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    mutex=k.CreateMutexW(None,False,'Global\\Tedd.RTree.PerformanceHost')
    if k.WaitForSingleObject(mutex,1000) not in (0,0x80):raise RuntimeError('Performance host busy')
    try:
        if not k.SetProcessAffinityMask(k.GetCurrentProcess(),4):raise ctypes.WinError(ctypes.get_last_error())
        if sys.argv[1]=='prepare':restore();generate();build();checks(full=True)
        elif sys.argv[1]=='construction':measure('construction',['control','binary','owned','split','rust'],3,191061)
        elif sys.argv[1]=='prepare-traversal':traversal(sys.argv[2])
        elif sys.argv[1]=='traversal':measure('traversal',[sys.argv[2],'overlap','iterative','rust'],3,191062,epoch='traversal')
        elif sys.argv[1]=='codegen':codegen(sys.argv[2],sys.argv[3:])
        elif sys.argv[1]=='prepare-remedies':remedies()
        elif sys.argv[1]=='remedies':measure('remedies',['control','ref','vector','combined','rust'],3,191063,epoch='remedies')
        elif sys.argv[1]=='prepare-query-remedies':query_remedies()
        elif sys.argv[1]=='query-remedies':measure('query-remedies',['control','stack','buffer','stack-buffer','predicate','predicate-buffer','rust'],3,191064,epoch='query-remedies')
        elif sys.argv[1]=='prepare-passes':construction_passes()
        elif sys.argv[1]=='passes':measure('passes',['vector','reduce','wide','wide-reduce','rust'],3,191065,epoch='passes')
        elif sys.argv[1]=='recover-query':recover_query()
        elif sys.argv[1]=='prepare-representation':representation(sys.argv[2])
        elif sys.argv[1]=='representation':measure('representation',[sys.argv[2],'normalized-scalar','normalized-vector','rust'],3,191066,epoch='representation')
        else:raise ValueError(sys.argv[1])
    finally:k.ReleaseMutex(mutex);k.CloseHandle(mutex)

if __name__=='__main__': main()
