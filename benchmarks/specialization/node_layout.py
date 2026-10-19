"""Prepare separately declared node-layout and key-SIMD research variants."""
from pathlib import Path
import shutil
ROOT=Path('D:/Workspaces/AI/rtree-specialization-20261019')
REPO=Path(__file__).resolve().parents[2]
REPORT=REPO/'Research/2026-10-19-specialization'

def once(t,a,b):
    if t.count(a)!=1:raise RuntimeError('Source drift: '+a[:70])
    return t.replace(a,b,1)

def generate():
    t=(REPORT/'PackedRTree.cs').read_text()
    t=t.replace('PackedRTree<T>','ColumnPackedRTree<T>').replace('public PackedRTree(', 'public ColumnPackedRTree(')
    t='using System.Numerics;\nusing System.Runtime.InteropServices;\nusing System.Runtime.Intrinsics;\n\n'+t
    t=once(t,'    private readonly Rectangle[] _boxes;','    private readonly double[] _minX, _minY, _maxX, _maxY;\n    private readonly int _width;')
    t=once(t,'bool partial = false, BulkLoadWorkspace? workspace = null)','bool partial = false, BulkLoadWorkspace? workspace = null, int vectorWidth = 256)')
    t=once(t,'        _capacity = maxEntries;','        _capacity = maxEntries;\n        _width = vectorWidth;')
    t=once(t,'_boxes = []; _values = [];','_minX = []; _minY = []; _maxX = []; _maxY = []; _values = [];')
    t=once(t,'        _boxes = new Rectangle[total];','        _minX = new double[total]; _minY = new double[total];\n        _maxX = new double[total]; _maxY = new double[total];')
    t=once(t,'            _boxes[i] = entry.Bounds;','            _minX[i] = entry.Bounds.MinX; _minY[i] = entry.Bounds.MinY;\n            _maxX[i] = entry.Bounds.MaxX; _maxY[i] = entry.Bounds.MaxY;')
    t=once(t,'''                Rectangle bounds = _boxes[first];
                for (int i = first + 1; i < end; i++) bounds = Rectangle.Union(bounds, _boxes[i]);
                _boxes[destination] = bounds;''','''                double minXValue = _minX[first], minYValue = _minY[first], maxXValue = _maxX[first], maxYValue = _maxY[first];
                for (int i = first + 1; i < end; i++)
                {
                    minXValue = Math.Min(minXValue, _minX[i]); minYValue = Math.Min(minYValue, _minY[i]);
                    maxXValue = Math.Max(maxXValue, _maxX[i]); maxYValue = Math.Max(maxYValue, _maxY[i]);
                }
                _minX[destination] = minXValue; _minY[destination] = minYValue;
                _maxX[destination] = maxXValue; _maxY[destination] = maxYValue;''')
    t=once(t,'_boxes.Length, bounds, results','_minX.Length, bounds, results')
    start=t.index('    private int SearchLevel(');end=t.index('    public List<T> Search(',start)
    t=t[:start]+'''    private int SearchLevel(int level, int start, int end, in Rectangle bounds, List<T> results)
    {
        int found = 0, i = start;
        // All four arrays have equal length. Tree-owned ranges satisfy
        // 0 <= start <= end <= length; only complete vectors are loaded.
        if (_width == 256 && Vector256.IsHardwareAccelerated)
        {
            var qMinX = Vector256.Create(bounds.MinX); var qMinY = Vector256.Create(bounds.MinY);
            var qMaxX = Vector256.Create(bounds.MaxX); var qMaxY = Vector256.Create(bounds.MaxY);
            for (; i <= end - 4; i += 4)
            {
                var matches = Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_minX), (nuint)i), qMaxX)
                    & Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_minY), (nuint)i), qMaxY)
                    & Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_maxX), (nuint)i), qMinX)
                    & Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_maxY), (nuint)i), qMinY);
                uint mask = matches.ExtractMostSignificantBits();
                while (mask != 0)
                {
                    int index = i + BitOperations.TrailingZeroCount(mask); mask &= mask - 1;
                    found += AppendMatch(level, index, bounds, results);
                }
            }
        }
        else if (_width != 0 && Vector128.IsHardwareAccelerated)
        {
            var qMinX = Vector128.Create(bounds.MinX); var qMinY = Vector128.Create(bounds.MinY);
            var qMaxX = Vector128.Create(bounds.MaxX); var qMaxY = Vector128.Create(bounds.MaxY);
            for (; i <= end - 2; i += 2)
            {
                var matches = Vector128.LessThanOrEqual(Vector128.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_minX), (nuint)i), qMaxX)
                    & Vector128.LessThanOrEqual(Vector128.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_minY), (nuint)i), qMaxY)
                    & Vector128.GreaterThanOrEqual(Vector128.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_maxX), (nuint)i), qMinX)
                    & Vector128.GreaterThanOrEqual(Vector128.LoadUnsafe(ref MemoryMarshal.GetArrayDataReference(_maxY), (nuint)i), qMinY);
                uint mask = matches.ExtractMostSignificantBits();
                while (mask != 0)
                {
                    int index = i + BitOperations.TrailingZeroCount(mask); mask &= mask - 1;
                    found += AppendMatch(level, index, bounds, results);
                }
            }
        }
        for (; i < end; i++)
            if (_minX[i] <= bounds.MaxX && _maxX[i] >= bounds.MinX && _minY[i] <= bounds.MaxY && _maxY[i] >= bounds.MinY)
                found += AppendMatch(level, i, bounds, results);
        return found;
    }

    private int AppendMatch(int level, int index, in Rectangle bounds, List<T> results)
    {
        if (level == 0) { results.Add(_values[index]); return 1; }
        int lowerStart = _starts[level - 1], lowerEnd = _starts[level];
        int local = index - lowerEnd;
        if (bounds.MinX <= _minX[index] && bounds.MinY <= _minY[index] && bounds.MaxX >= _maxX[index] && bounds.MaxY >= _maxY[index])
        {
            int first = local * _spans[level];
            int count = Math.Min(_spans[level], Count - first);
            results.AddRange(_values.AsSpan(first, count)); return count;
        }
        int child = lowerStart + local * _capacity;
        return SearchLevel(level - 1, child, child + Math.Min(_capacity, lowerEnd - child), bounds, results);
    }

'''+t[end:]
    (REPORT/'ColumnPackedRTree.cs').write_text(t,encoding='utf8',newline='\n')

def key_source():
    source=ROOT/'library-source/src/Tedd.RTree'
    old=(ROOT/'retained/keyvector-source/src/Tedd.RTree/RTree.cs').read_text()
    body=old[old.index('        Span<uint> xs ='):old.index('        // Primitive keys')]
    body=body.replace('itemCount','Count').replace('items[','source[').replace('finiteScaleX','finiteX').replace('finiteScaleY','finiteY')
    t=(REPORT/'PackedRTree.cs').read_text()
    t='using System.Runtime.Intrinsics;\n\n'+t
    t=t.replace('PackedRTree<T>','KeyPackedRTree<T>').replace('public PackedRTree(', 'public KeyPackedRTree(')
    start=t.index('        for (int i = 0; i < Count; i++)');end=t.index('        if (!partial',start)
    t=t[:start]+body+t[end:]
    (REPORT/'KeyPackedRTree.cs').write_text(t,encoding='utf8',newline='\n')
    (source/'KeyPackedRTree.cs').write_text(t,encoding='utf8',newline='\n')
    shutil.copyfile(ROOT/'retained/keyvector-source/src/Tedd.RTree/HilbertOrder.cs',source/'HilbertOrder.cs')

if __name__=='__main__':generate()
