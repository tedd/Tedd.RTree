"""Reproducible collection candidates, generated from the frozen control."""
from pathlib import Path
import shutil

ROOT=Path('D:/Workspaces/AI/rtree-simd-20261018')

def replace_once(text, old, new):
    if text.count(old)!=1: raise RuntimeError('Source shape drift: '+old[:90])
    return text.replace(old,new,1)

def create(stage):
    destination=ROOT/f'{stage}-source/src/Tedd.RTree'
    destination.mkdir(parents=True,exist_ok=False)
    if stage=='keyinline':
        for file in (ROOT/'keyvector-source/src/Tedd.RTree').iterdir():
            if file.suffix in ('.cs','.csproj'): shutil.copyfile(file,destination/file.name)
        for name,method in (('HilbertOrder.cs','Encode'),('SpatialOrder3D.cs','Morton')):
            p=destination/name
            text='using System.Runtime.CompilerServices;\n\n'+p.read_text()
            text=replace_once(text,'    internal static Vector256<uint> '+method+'(',
                '    [MethodImpl(MethodImplOptions.AggressiveInlining)]\n    internal static Vector256<uint> '+method+'(')
            p.write_text(text)
        return
    if stage=='keyvector':
        import re
        for file in (ROOT/'selected-source/src/Tedd.RTree').iterdir():
            if file.suffix in ('.cs','.csproj'): shutil.copyfile(file,destination/file.name)
        for name,method,arity in (('HilbertOrder.cs','Encode',2),('SpatialOrder3D.cs','Morton',3)):
            p=destination/name
            text='using System.Runtime.Intrinsics;\n\n'+p.read_text()
            start=text.index('    internal static uint '+method+'(')
            methods=text[start:text.rfind('}')]
            if method=='Encode':
                # Keep the exact scalar expression tree, lifting independent axes
                # into eight lanes. No floating-point arithmetic is reassociated.
                methods=methods[:methods.index('    private static uint Spread')]+methods[methods.index('    private static uint Spread'):]
            methods=re.sub(r'\buint\b','Vector256<uint>',methods)
            methods=re.sub(r'\b0x[0-9A-Fa-f]+\b',lambda m:'Vector256.Create('+m[0]+'u)',methods)
            p.write_text(text[:text.rfind('}')]+methods+'}\n')
        for name,shape,axes in (('RTree.cs','Rectangle',2),('RTree2D.Generic.cs','Rectangle2D<TCoordinate>',2),('RTree3D.Generic.cs','Box<TCoordinate>',3)):
            p=destination/name
            text='using System.Runtime.Intrinsics;\n\n'+p.read_text()
            start=text.index('        for (int i = 0; i < itemCount; i++)\n        {',text.index('        bool finiteScaleX') if name=='RTree.cs' else text.index('        var axisY'))
            end=text.index('        // Primitive keys',start)
            scalar=text[start:end]
            body=scalar[scalar.index('        {')+10:scalar.rfind('        }')]
            # The scalar body begins with a newline; retain its exact quantization.
            body=body.replace('items[i]','items[index]').replace('            order[i] = i;','            order[index] = index;')
            if name=='RTree.cs':
                body=replace_once(body,'            keys[i] = HilbertOrder.Encode(ix, iy);','            xs[lane] = ix; ys[lane] = iy;')
            elif axes==2:
                body=replace_once(body,'            keys[i] = HilbertOrder.Encode(axisX.Center(b.MinX, b.MaxX), axisY.Center(b.MinY, b.MaxY));',
                    '            xs[lane] = axisX.Center(b.MinX, b.MaxX); ys[lane] = axisY.Center(b.MinY, b.MaxY);')
            else:
                body=replace_once(body,'            keys[i] = SpatialOrder3D.Morton(axisX.Center(b.MinX, b.MaxX), axisY.Center(b.MinY, b.MaxY), axisZ.Center(b.MinZ, b.MaxZ));',
                    '            xs[lane] = axisX.Center(b.MinX, b.MaxX); ys[lane] = axisY.Center(b.MinY, b.MaxY); zs[lane] = axisZ.Center(b.MinZ, b.MaxZ);')
            declarations='        Span<uint> xs = stackalloc uint[8], ys = stackalloc uint[8];\n'
            if axes==3: declarations+='        Span<uint> zs = stackalloc uint[8];\n'
            encode='HilbertOrder.Encode(Vector256.Create(xs), Vector256.Create(ys))' if axes==2 else 'SpatialOrder3D.Morton(Vector256.Create(xs), Vector256.Create(ys), Vector256.Create(zs))'
            vector=declarations+'''        int vectorCount = Vector256.IsHardwareAccelerated ? itemCount & ~7 : 0;
        for (int first = 0; first < vectorCount; first += 8)
        {
            for (int lane = 0; lane < 8; lane++)
            {
                int index = first + lane;
'''+body+'''            }
            '''+encode+'''.CopyTo(keys.Slice(first, 8));
        }
'''
            text=text[:start]+vector+scalar.replace('int i = 0;', 'int i = vectorCount;',1)+text[end:]
            p.write_text(text)
        return
    if stage=='filled':
        for file in (ROOT/'selected-source/src/Tedd.RTree').iterdir():
            if file.suffix in ('.cs','.csproj'): shutil.copyfile(file,destination/file.name)
        for name,shape,entry in (('RTree.cs','Rectangle','SpatialEntry<T>'),
                ('RTree2D.Generic.cs','Rectangle2D<TCoordinate>','SpatialEntry2D<TCoordinate, T>'),
                ('RTree3D.Generic.cs','Box<TCoordinate>','SpatialEntry3D<TCoordinate, T>')):
            p=destination/name
            text=p.read_text()
            old=f'''            for (int i = start; i < end; i++)
            {{
                {entry} item = items[order[i]];
                Add(node, new Entry(item.Bounds, null, item.Item));
            }}
            node.PackedCount = node.Count;'''
            new=f'''            int count = end - start;
            Span<{shape}> boxes = node.Boxes.AsSpan(0, count);
            Span<T> values = packedValues.AsSpan(start, count);
            {entry} first = items[order[start]];
            boxes[0] = first.Bounds;
            values[0] = first.Item;
            {shape} bounds = first.Bounds;
            // Accumulate bounds locally instead of rewriting node fields for every item.
            for (int i = 1; i < count; i++)
            {{
                {entry} item = items[order[start + i]];
                boxes[i] = item.Bounds;
                values[i] = item.Item;
                bounds = {shape}.Union(bounds, item.Bounds);
            }}
            node.Count = count;
            node.Bounds = bounds;
            node.PackedCount = count;'''
            p.write_text(replace_once(text,old,new))
        return
    if stage=='chunked':
        for file in (ROOT/'selected-source/src/Tedd.RTree').iterdir():
            if file.suffix in ('.cs','.csproj'): shutil.copyfile(file,destination/file.name)
        for name in ('RTree.cs','RTree2D.Generic.cs','RTree3D.Generic.cs'):
            p=destination/name
            text=p.read_text()
            if 'using System.Runtime.CompilerServices;' not in text:
                text='using System.Runtime.CompilerServices;\n\n'+text
            text=replace_once(text,'        T[] packedValues = new T[itemCount];','''        // Keep ordinary-sized value chunks below 64 KiB of payload. A power
        // of node capacity aligns chunk boundaries with complete packed subtrees.
        int valueLimit = Math.Max(_capacity, 65536 / Unsafe.SizeOf<T>());
        int chunkCapacity = _capacity;
        while (chunkCapacity <= valueLimit / _capacity) chunkCapacity *= _capacity;
        T[] packedValues = Array.Empty<T>();
        int valueStart = 0;''')
            text=replace_once(text,'            Node node = new(true, _capacity, packedValues, start);','''            if (valueStart == packedValues.Length)
            {
                packedValues = new T[Math.Min(chunkCapacity, itemCount - start)];
                valueStart = 0;
            }
            Node node = new(true, _capacity, packedValues, valueStart);''')
            text=replace_once(text,'            node.PackedCount = node.Count;','            valueStart += node.Count;\n            node.PackedCount = node.Count;')
            text=replace_once(text,'''                parent.Values = packedValues;
                parent.ValueStart = level[start].ValueStart;
                parent.PackedCount = level[end - 1].ValueStart + level[end - 1].PackedCount - parent.ValueStart;''','''                Node first = level[start], last = level[end - 1];
                // Chunks are consecutive and never reused. Matching endpoints
                // therefore prove that every intervening value has one owner.
                if (first.PackedCount != 0 && ReferenceEquals(first.Values, last.Values))
                {
                    parent.Values = first.Values;
                    parent.ValueStart = first.ValueStart;
                    parent.PackedCount = last.ValueStart + last.PackedCount - parent.ValueStart;
                }''')
            p.write_text(text)
        return
    for file in (ROOT/'baseline-source/src/Tedd.RTree').iterdir():
        if file.suffix in ('.cs','.csproj'): shutil.copyfile(file,destination/file.name)
    path=destination/'RTree.cs'
    source=path.read_text()
    if stage=='counted':
        for name in ('RTree.cs','RTree2D.Generic.cs','RTree3D.Generic.cs'):
            p=destination/name
            text='using System.Runtime.InteropServices;\n\n'+p.read_text()
            text=replace_once(text,'        internal readonly bool Leaf = leaf;',
                '        internal bool Leaf => Children is null;\n        internal int PackedCount;')
            text=replace_once(text,'            level[n] = node;','            node.PackedCount = node.Count;\n            level[n] = node;')
            text=replace_once(text,'''                for (int i = start; i < end; i++)
                    Add(parent, new Entry(level[i].Bounds, level[i], default!));''','''                for (int i = start; i < end; i++)
                {
                    Add(parent, new Entry(level[i].Bounds, level[i], default!));
                    parent.PackedCount += level[i].PackedCount;
                }''')
            text=replace_once(text,'        return Search(_root, bounds, results);',
                '        return _root.PackedCount != 0 && bounds.Contains(_root.Bounds) ? CollectValues(_root, results) : Search(_root, bounds, results);')
            text=replace_once(text,'''        int found = 0;
        for (int i = 0; i < node.Count; i++) found += CollectValues(node.Children![i]!, results);''','''        if (node.PackedCount != 0)
        {
            int start = results.Count;
            int end = checked(start + node.PackedCount);
            results.EnsureCapacity(end);
            CollectionsMarshal.SetCount(results, end);
            CopyValues(node, CollectionsMarshal.AsSpan(results).Slice(start, node.PackedCount));
            return node.PackedCount;
        }
        int found = 0;
        for (int i = 0; i < node.Count; i++) found += CollectValues(node.Children![i]!, results);''')
            at=text.index('    private static int Search(Node node,')
            text=text[:at]+'''    private static int CopyValues(Node node, Span<T> destination)
    {
        if (node.Leaf)
        {
            node.Values!.AsSpan(0, node.Count).CopyTo(destination);
            return node.Count;
        }
        int offset = 0;
        for (int i = 0; i < node.Count; i++)
            offset += CopyValues(node.Children![i]!, destination.Slice(offset));
        return offset;
    }

'''+text[at:]
            text=replace_once(text,'            if (!Remove(child, bounds, item, reinserts)) continue;',
                '            if (!Remove(child, bounds, item, reinserts)) continue;\n            node.PackedCount = 0;')
            text=replace_once(text,'    private static void RemoveAt(Node node, int index)\n    {',
                '    private static void RemoveAt(Node node, int index)\n    {\n        node.PackedCount = 0;')
            text=replace_once(text,'    private void Insert(Node node, Entry entry, out Node? sibling)\n    {',
                '    private void Insert(Node node, Entry entry, out Node? sibling)\n    {\n        node.PackedCount = 0;')
            p.write_text(text)
        return
    if stage=='runs':
        old='''            for (int i = 0; i < entries.Length; i++)
            {
                ref readonly Rectangle entry = ref entries[i];
                if (entry.Intersects(bounds))
                {
                    results.Add(node.Values![i]);
                    found++;
                }
            }'''
        new='''            int i = 0;
            while (i < entries.Length)
            {
                if (!entries[i].Intersects(bounds)) { i++; continue; }
                int start = i++;
                while (i < entries.Length && entries[i].Intersects(bounds)) i++;
                results.AddRange(node.Values!.AsSpan(start, i - start));
                found += i - start;
            }'''
        source=replace_once(source,old,new)
    elif stage=='ranges':
        source=ranges(source)
    elif stage in ('ranges-fixed','ranges-raw'):
        for name in ('RTree.cs','RTree2D.Generic.cs','RTree3D.Generic.cs'):
            p=destination/name
            text=ranges(p.read_text())
            text=replace_once(text,'''            for (int i = 0; i < node.Count; i++) entries.Add(ReadEntry(node, i));''','''            for (int i = 0; i < node.Count; i++) entries.Add(ReadEntry(node, i));
            // This entire subtree is discarded after collecting its entries.
            // Release shared slots even for leaves never individually mutated.
            if (node.PackedCount != 0)
                node.Values!.AsSpan(node.ValueStart, node.Count).Clear();''')
            text=replace_once(text,'return bounds.Contains(_root.Bounds) ? CollectValues(_root, results) : Search(_root, bounds, results);',
                'return _root.PackedCount != 0 && bounds.Contains(_root.Bounds) ? CollectValues(_root, results) : Search(_root, bounds, results);')
            text=text.replace('            MakeWritable(node);','            if (node.PackedCount != 0) MakeWritable(node);')
            text=text.replace('        MakeWritable(node);','        if (node.PackedCount != 0) MakeWritable(node);')
            text=replace_once(text,'        if (node.PackedCount == 0) return;\n','')
            if stage=='ranges-raw':
                text=replace_once(text,'            ReadOnlySpan<T> values = node.Values!.AsSpan(node.ValueStart, node.Count);\n','')
                text=replace_once(text,'results.Add(values[i]);','results.Add(node.Values![node.ValueStart + i]);')
            p.write_text(text)
        return
    elif stage in ('pdep','histogram'):
        if stage=='pdep':
            for name,mask in (('HilbertOrder.cs','0x55555555u'),('SpatialOrder3D.cs','0x09249249u')):
                p=destination/name
                text='using System.Runtime.Intrinsics.X86;\n\n'+p.read_text()
                text=replace_once(text,'    private static uint Spread(uint x)\n    {',
                    '    private static uint Spread(uint x)\n    {\n        if (Bmi2.IsSupported) return Bmi2.ParallelBitDeposit(x, '+mask+');')
                p.write_text(text)
        else:
            p=destination/'HilbertOrder.cs'
            text=p.read_text()
            text=replace_once(text,'        Span<int> offsets = stackalloc int[256];','''        Span<int> histograms = stackalloc int[1024];
        histograms.Clear();
        // A byte histogram is invariant under permutation. Count all passes once,
        // reading primitive keys sequentially instead of following each permutation.
        foreach (uint key in keys)
        {
            histograms[(int)(key & 255)]++;
            histograms[256 + (int)((key >> 8) & 255)]++;
            histograms[512 + (int)((key >> 16) & 255)]++;
            histograms[768 + (int)(key >> 24)]++;
        }''')
            text=replace_once(text,'''            offsets.Clear();
            for (int i = 0; i < order.Length; i++) offsets[(int)(keys[order[i]] >> shift) & 255]++;''',
                '            Span<int> offsets = histograms.Slice(shift * 32, 256);')
            p.write_text(text)
    else: raise RuntimeError(stage)
    path.write_text(source)

def ranges(source):
    source=replace_once(source,'private sealed class Node(bool leaf, int capacity)',
                        'private sealed class Node(bool leaf, int capacity, T[]? packedValues = null, int valueStart = 0)')
    source=replace_once(source,'// Leaves never carry child references; branches never carry user values.',
                        '// Packed nodes share contiguous values; mutation detaches only the affected leaf.')
    source=replace_once(source,'internal readonly T[]? Values = leaf ? new T[capacity + 1] : null;',
                        'internal T[]? Values = packedValues ?? (leaf ? new T[capacity + 1] : null);\n        internal int ValueStart = valueStart;\n        internal int PackedCount;')
    source=replace_once(source,'        Node[] level = new Node[(itemCount - 1) / _capacity + 1];',
                        '        T[] packedValues = new T[itemCount];\n        Node[] level = new Node[(itemCount - 1) / _capacity + 1];')
    source=replace_once(source,'            Node node = new(true, _capacity);','            Node node = new(true, _capacity, packedValues, start);')
    source=replace_once(source,'            level[n] = node;','            node.PackedCount = node.Count;\n            level[n] = node;')
    source=replace_once(source,'                parents[n] = parent;','''                parent.Values = packedValues;
                parent.ValueStart = level[start].ValueStart;
                parent.PackedCount = level[end - 1].ValueStart + level[end - 1].PackedCount - parent.ValueStart;
                parents[n] = parent;''')
    source=replace_once(source,'        return Search(_root, bounds, results);',
                        '        return bounds.Contains(_root.Bounds) ? CollectValues(_root, results) : Search(_root, bounds, results);')
    source=replace_once(source,'''        if (node.Leaf)
        {
            results.AddRange(node.Values!.AsSpan(0, node.Count));
            return node.Count;
        }''','''        if (node.Leaf || node.PackedCount != 0)
        {
            int count = node.Leaf ? node.Count : node.PackedCount;
            results.AddRange(node.Values!.AsSpan(node.ValueStart, count));
            return count;
        }''')
    # Only partial leaf traversal needs individual values; validate that active slice once.
    search=source.index('    private static int Search(Node node,')
    end=source.index('    private bool Remove(Node node,',search)
    part=source[search:end]
    part=replace_once(part,'''        if (node.Leaf)
        {
            for''','''        if (node.Leaf)
        {
            ReadOnlySpan<T> values = node.Values!.AsSpan(node.ValueStart, node.Count);
            for''')
    part=replace_once(part,'results.Add(node.Values![i]);','results.Add(values[i]);')
    source=source[:search]+part+source[end:]
    source=replace_once(source,'            if (!Remove(child, bounds, item, reinserts)) continue;',
                        '            if (!Remove(child, bounds, item, reinserts)) continue;\n            MakeWritable(node);')
    source=replace_once(source,'''    private static void RemoveAt(Node node, int index)
    {
        int last''','''    private static void RemoveAt(Node node, int index)
    {
        MakeWritable(node);
        int last''')
    source=replace_once(source,'''    private void Insert(Node node, Entry entry, out Node? sibling)
    {
        if''','''    private void Insert(Node node, Entry entry, out Node? sibling)
    {
        MakeWritable(node);
        if''')
    source=replace_once(source,'if (node.Leaf) node.Values![index] = entry.Value;',
                        'if (node.Leaf) node.Values![node.ValueStart + index] = entry.Value;')
    source=replace_once(source,'node.Leaf ? node.Values![index] : default!',
                        'node.Leaf ? node.Values![node.ValueStart + index] : default!')
    at=source.index('    private static void Add(Node node, Entry entry)')
    helper='''    private static void MakeWritable(Node node)
    {
        if (node.PackedCount == 0) return;
        if (node.Leaf)
        {
            T[] values = new T[node.Boxes.Length];
            Span<T> original = node.Values!.AsSpan(node.ValueStart, node.Count);
            original.CopyTo(values);
            // Every ancestor range is invalidated by the mutating path. No live range
            // overlaps this detached leaf; clear its old slots to release references.
            original.Clear();
            node.Values = values;
            node.ValueStart = 0;
        }
        else node.Values = null;
        node.PackedCount = 0;
    }

'''
    return source[:at]+helper+source[at:]

if __name__=='__main__':
    import sys
    create(sys.argv[1])
