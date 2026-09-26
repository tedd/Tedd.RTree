using System.Numerics;
using System.Runtime.InteropServices;
using System.Runtime.Intrinsics;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using Tedd.RTree;

// Experimental alternatives. These types are benchmark fixtures, not the library API.
internal sealed class LinearIndex
{
    private readonly Rectangle[] _bounds;
    private readonly double[] _minX, _minY, _maxX, _maxY;
    private readonly ulong[] _xLow, _xHigh, _yLow, _yHigh;

    internal LinearIndex(Rectangle[] bounds)
    {
        _bounds = bounds;
        _minX = new double[bounds.Length];
        _minY = new double[bounds.Length];
        _maxX = new double[bounds.Length];
        _maxY = new double[bounds.Length];
        int words = (bounds.Length + 63) / 64;
        _xLow = new ulong[words];
        _xHigh = new ulong[words];
        _yLow = new ulong[words];
        _yHigh = new ulong[words];
        for (int i = 0; i < bounds.Length; i++)
        {
            _minX[i] = bounds[i].MinX;
            _minY[i] = bounds[i].MinY;
            _maxX[i] = bounds[i].MaxX;
            _maxY[i] = bounds[i].MaxY;
        }
    }

    internal int Scalar(Rectangle query, List<int> results)
    {
        int before = results.Count;
        for (int i = 0; i < _bounds.Length; i++)
            if (_bounds[i].Intersects(query)) results.Add(i);
        return results.Count - before;
    }

    internal int Simd(Rectangle query, List<int> results)
    {
        int before = results.Count;
        int i = 0;
        if (Vector256.IsHardwareAccelerated)
        {
            Vector256<double> qMinX = Vector256.Create(query.MinX);
            Vector256<double> qMinY = Vector256.Create(query.MinY);
            Vector256<double> qMaxX = Vector256.Create(query.MaxX);
            Vector256<double> qMaxY = Vector256.Create(query.MaxY);
            for (; i <= _bounds.Length - 4; i += 4)
            {
                Vector256<double> match =
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref _minX[i]), qMaxX) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref _maxX[i]), qMinX) &
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref _minY[i]), qMaxY) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref _maxY[i]), qMinY);
                uint bits = match.ExtractMostSignificantBits();
                while (bits != 0)
                {
                    results.Add(i + BitOperations.TrailingZeroCount(bits));
                    bits &= bits - 1;
                }
            }
        }
        for (; i < _bounds.Length; i++)
            if (_bounds[i].Intersects(query)) results.Add(i);
        return results.Count - before;
    }

    internal int SimdByRef(Rectangle query, List<int> results)
    {
        int before = results.Count;
        int i = 0;
        if (Vector256.IsHardwareAccelerated)
        {
            Vector256<double> qMinX = Vector256.Create(query.MinX);
            Vector256<double> qMinY = Vector256.Create(query.MinY);
            Vector256<double> qMaxX = Vector256.Create(query.MaxX);
            Vector256<double> qMaxY = Vector256.Create(query.MaxY);
            // All four arrays are created at exactly _bounds.Length in the constructor.
            // The loop reads only complete four-element groups inside that length.
            ref double x0 = ref MemoryMarshal.GetArrayDataReference(_minX);
            ref double x1 = ref MemoryMarshal.GetArrayDataReference(_maxX);
            ref double y0 = ref MemoryMarshal.GetArrayDataReference(_minY);
            ref double y1 = ref MemoryMarshal.GetArrayDataReference(_maxY);
            for (; i <= _bounds.Length - 4; i += 4)
            {
                Vector256<double> match =
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref x0, (nuint)i), qMaxX) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref x1, (nuint)i), qMinX) &
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref y0, (nuint)i), qMaxY) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref y1, (nuint)i), qMinY);
                uint bits = match.ExtractMostSignificantBits();
                while (bits != 0)
                {
                    results.Add(i + BitOperations.TrailingZeroCount(bits));
                    bits &= bits - 1;
                }
            }
        }
        for (; i < _bounds.Length; i++)
            if (_bounds[i].Intersects(query)) results.Add(i);
        return results.Count - before;
    }

    internal int OneBitmap(Rectangle query, List<int> results)
    {
        int before = results.Count;
        int i = 0;
        if (Vector256.IsHardwareAccelerated)
        {
            Vector256<double> qMinX = Vector256.Create(query.MinX);
            Vector256<double> qMinY = Vector256.Create(query.MinY);
            Vector256<double> qMaxX = Vector256.Create(query.MaxX);
            Vector256<double> qMaxY = Vector256.Create(query.MaxY);
            ref double x0 = ref MemoryMarshal.GetArrayDataReference(_minX);
            ref double x1 = ref MemoryMarshal.GetArrayDataReference(_maxX);
            ref double y0 = ref MemoryMarshal.GetArrayDataReference(_minY);
            ref double y1 = ref MemoryMarshal.GetArrayDataReference(_maxY);
            for (int start = 0; start < _bounds.Length; start += 64)
            {
                int end = Math.Min(start + 64, _bounds.Length);
                int shift = 0;
                ulong bits = 0;
                for (; i <= end - 4; i += 4, shift += 4)
                {
                    Vector256<double> match =
                        Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref x0, (nuint)i), qMaxX) &
                        Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref x1, (nuint)i), qMinX) &
                        Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref y0, (nuint)i), qMaxY) &
                        Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref y1, (nuint)i), qMinY);
                    bits |= (ulong)match.ExtractMostSignificantBits() << shift;
                }
                for (; i < end; i++, shift++)
                    if (_bounds[i].Intersects(query)) bits |= 1UL << shift;
                while (bits != 0)
                {
                    results.Add(start + BitOperations.TrailingZeroCount(bits));
                    bits &= bits - 1;
                }
            }
        }
        else
        {
            for (; i < _bounds.Length; i++)
                if (_bounds[i].Intersects(query)) results.Add(i);
        }
        return results.Count - before;
    }

    // Materialize one bitmap per corner predicate, then combine the four words.
    internal int Bitmap(Rectangle query, List<int> results)
    {
        int before = results.Count;
        int i = 0;
        if (Vector256.IsHardwareAccelerated)
        {
            Vector256<double> qMinX = Vector256.Create(query.MinX);
            Vector256<double> qMinY = Vector256.Create(query.MinY);
            Vector256<double> qMaxX = Vector256.Create(query.MaxX);
            Vector256<double> qMaxY = Vector256.Create(query.MaxY);
            for (int word = 0; word < _xLow.Length; word++)
            {
                ulong a = 0, b = 0, c = 0, d = 0;
                int end = Math.Min(i + 64, _bounds.Length);
                int shift = 0;
                for (; i <= end - 4; i += 4, shift += 4)
                {
                    a |= (ulong)Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref _minX[i]), qMaxX).ExtractMostSignificantBits() << shift;
                    b |= (ulong)Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref _maxX[i]), qMinX).ExtractMostSignificantBits() << shift;
                    c |= (ulong)Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref _minY[i]), qMaxY).ExtractMostSignificantBits() << shift;
                    d |= (ulong)Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref _maxY[i]), qMinY).ExtractMostSignificantBits() << shift;
                }
                for (; i < end; i++, shift++)
                {
                    ulong bit = 1UL << shift;
                    if (_minX[i] <= query.MaxX) a |= bit;
                    if (_maxX[i] >= query.MinX) b |= bit;
                    if (_minY[i] <= query.MaxY) c |= bit;
                    if (_maxY[i] >= query.MinY) d |= bit;
                }
                _xLow[word] = a;
                _xHigh[word] = b;
                _yLow[word] = c;
                _yHigh[word] = d;
            }
        }
        else
        {
            // The scalar fallback writes all logical bits before the merge.
            for (int word = 0; word < _xLow.Length; word++)
            {
                ulong a = 0, b = 0, c = 0, d = 0;
                int end = Math.Min((word + 1) * 64, _bounds.Length);
                for (int j = word * 64; j < end; j++)
                {
                    ulong bit = 1UL << (j & 63);
                    if (_minX[j] <= query.MaxX) a |= bit;
                    if (_maxX[j] >= query.MinX) b |= bit;
                    if (_minY[j] <= query.MaxY) c |= bit;
                    if (_maxY[j] >= query.MinY) d |= bit;
                }
                _xLow[word] = a; _xHigh[word] = b; _yLow[word] = c; _yHigh[word] = d;
            }
        }
        for (int word = 0; word < _xLow.Length; word++)
        {
            ulong bits = _xLow[word] & _xHigh[word] & _yLow[word] & _yHigh[word];
            while (bits != 0)
            {
                results.Add(word * 64 + BitOperations.TrailingZeroCount(bits));
                bits &= bits - 1;
            }
        }
        return results.Count - before;
    }
}

internal static class ByteSpanScan
{
    internal static int RequiredBytes(int count) => checked(count * 4 * sizeof(double));

    internal static void Fill(ReadOnlySpan<Rectangle> source, Span<byte> storage)
    {
        int planeBytes = checked(source.Length * sizeof(double));
        if (storage.Length < RequiredBytes(source.Length))
            throw new ArgumentException("Insufficient storage.", nameof(storage));
        Span<double> minX = MemoryMarshal.Cast<byte, double>(storage.Slice(0, planeBytes));
        Span<double> maxX = MemoryMarshal.Cast<byte, double>(storage.Slice(planeBytes, planeBytes));
        Span<double> minY = MemoryMarshal.Cast<byte, double>(storage.Slice(2 * planeBytes, planeBytes));
        Span<double> maxY = MemoryMarshal.Cast<byte, double>(storage.Slice(3 * planeBytes, planeBytes));
        for (int i = 0; i < source.Length; i++)
        {
            minX[i] = source[i].MinX;
            maxX[i] = source[i].MaxX;
            minY[i] = source[i].MinY;
            maxY[i] = source[i].MaxY;
        }
    }

    internal static int Search(ReadOnlySpan<byte> storage, int count, Rectangle query, List<int> results)
    {
        int planeBytes = checked(count * sizeof(double));
        if (storage.Length < RequiredBytes(count))
            throw new ArgumentException("Insufficient storage.", nameof(storage));
        ReadOnlySpan<double> minX = MemoryMarshal.Cast<byte, double>(storage.Slice(0, planeBytes));
        ReadOnlySpan<double> maxX = MemoryMarshal.Cast<byte, double>(storage.Slice(planeBytes, planeBytes));
        ReadOnlySpan<double> minY = MemoryMarshal.Cast<byte, double>(storage.Slice(2 * planeBytes, planeBytes));
        ReadOnlySpan<double> maxY = MemoryMarshal.Cast<byte, double>(storage.Slice(3 * planeBytes, planeBytes));
        int before = results.Count;
        int i = 0;
        if (Vector256.IsHardwareAccelerated)
        {
            Vector256<double> qMinX = Vector256.Create(query.MinX);
            Vector256<double> qMinY = Vector256.Create(query.MinY);
            Vector256<double> qMaxX = Vector256.Create(query.MaxX);
            Vector256<double> qMaxY = Vector256.Create(query.MaxY);
            ref double x0 = ref MemoryMarshal.GetReference(minX);
            ref double x1 = ref MemoryMarshal.GetReference(maxX);
            ref double y0 = ref MemoryMarshal.GetReference(minY);
            ref double y1 = ref MemoryMarshal.GetReference(maxY);
            for (; i <= count - 4; i += 4)
            {
                Vector256<double> match =
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref x0, (nuint)i), qMaxX) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref x1, (nuint)i), qMinX) &
                    Vector256.LessThanOrEqual(Vector256.LoadUnsafe(ref y0, (nuint)i), qMaxY) &
                    Vector256.GreaterThanOrEqual(Vector256.LoadUnsafe(ref y1, (nuint)i), qMinY);
                uint bits = match.ExtractMostSignificantBits();
                while (bits != 0)
                {
                    results.Add(i + BitOperations.TrailingZeroCount(bits));
                    bits &= bits - 1;
                }
            }
        }
        for (; i < count; i++)
            if (minX[i] <= query.MaxX && maxX[i] >= query.MinX &&
                minY[i] <= query.MaxY && maxY[i] >= query.MinY) results.Add(i);
        return results.Count - before;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class ScanHypothesisBenchmarks
{
    [Params(32, 256, 1_000, 10_000)] public int Size { get; set; }
    [Params("Point", "Broad")] public string QueryWidth { get; set; } = "Point";

    private Rectangle[] _bounds = null!;
    private Rectangle[] _queries = null!;
    private RTree<int> _tree = null!;
    private LinearIndex _linear = null!;
    private readonly List<int> _results = [];
    private Func<Rectangle, List<int>, int> _treeSearch = null!;
    private Func<Rectangle, List<int>, int> _scalarSearch = null!;
    private Func<Rectangle, List<int>, int> _simdSearch = null!;
    private Func<Rectangle, List<int>, int> _bitmapSearch = null!;
    private Func<Rectangle, List<int>, int> _oneBitmapSearch = null!;
    private Func<Rectangle, List<int>, int> _simdByRefSearch = null!;

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _bounds = new Rectangle[Size];
        SpatialEntry<int>[] entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _bounds[i] = new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            entries[i] = new SpatialEntry<int>(_bounds[i], i);
        }
        _queries = new Rectangle[64];
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            double width = QueryWidth == "Point" ? 0 : 1000;
            _queries[i] = new Rectangle(x, y, x + width, y + width);
        }
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _linear = new LinearIndex(_bounds);
        _treeSearch = _tree.Search;
        _scalarSearch = _linear.Scalar;
        _simdSearch = _linear.Simd;
        _bitmapSearch = _linear.Bitmap;
        _oneBitmapSearch = _linear.OneBitmap;
        _simdByRefSearch = _linear.SimdByRef;
        foreach (Rectangle query in _queries)
        {
            int[] expected = Enumerable.Range(0, Size).Where(i => _bounds[i].Intersects(query)).ToArray();
            foreach (Func<Rectangle, List<int>, int> search in new Func<Rectangle, List<int>, int>[]
                     { _treeSearch, _scalarSearch, _simdSearch, _simdByRefSearch, _bitmapSearch, _oneBitmapSearch })
            {
                _results.Clear();
                if (search(query, _results) != expected.Length || !_results.Order().SequenceEqual(expected))
                    throw new InvalidOperationException("Candidate returned incorrect entries.");
            }
        }
    }

    private int Query(Func<Rectangle, List<int>, int> search)
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += search(query, _results);
        }
        return total;
    }

    [Benchmark(Baseline = true)] public int PackedTree() => Query(_treeSearch);
    [Benchmark] public int ScalarScan() => Query(_scalarSearch);
    [Benchmark] public int SimdScan() => Query(_simdSearch);
    [Benchmark] public int FourBitmaps() => Query(_bitmapSearch);
    [Benchmark] public int OneBitmap() => Query(_oneBitmapSearch);
    [Benchmark] public int SimdByRef() => Query(_simdByRefSearch);
}

internal sealed class RecentQueryCache
{
    private readonly RTree<int> _tree = new();
    private readonly Rectangle[] _keys = new Rectangle[4];
    private readonly List<int>[] _values = [[], [], [], []];
    private readonly bool[] _valid = new bool[4];
    private int _next;

    internal void BulkLoad(SpatialEntry<int>[] entries)
    {
        _tree.BulkLoad(entries);
        Array.Clear(_valid);
    }

    internal void Insert(Rectangle bounds, int value)
    {
        _tree.Insert(bounds, value);
        Array.Clear(_valid);
    }

    internal int Search(Rectangle query, List<int> results)
    {
        for (int i = 0; i < 4; i++)
            if (_valid[i] && _keys[i] == query)
            {
                results.AddRange(_values[i]);
                return _values[i].Count;
            }
        int slot = _next;
        _next = (_next + 1) & 3;
        _keys[slot] = query;
        _values[slot].Clear();
        int found = _tree.Search(query, _values[slot]);
        _valid[slot] = true;
        results.AddRange(_values[slot]);
        return found;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class RecentQueryCacheBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    [Params("Repeated4", "Unique64")] public string Pattern { get; set; } = "Repeated4";

    private Rectangle[] _queries = null!;
    private RTree<int> _tree = null!;
    private RecentQueryCache _cache = null!;
    private readonly List<int> _results = [];

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        SpatialEntry<int>[] entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            entries[i] = new SpatialEntry<int>(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        Rectangle[] distinct = new Rectangle[64];
        for (int i = 0; i < distinct.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            double width = i % 4 switch { 0 => 0, 1 => 20, 2 => 200, _ => 1000 };
            distinct[i] = new Rectangle(x, y, x + width, y + width);
        }
        _queries = Pattern == "Repeated4"
            ? Enumerable.Range(0, 64).Select(i => distinct[i % 4]).ToArray()
            : distinct;
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _cache = new RecentQueryCache();
        _cache.BulkLoad(entries);
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            _tree.Search(query, _results);
            int[] expected = _results.Order().ToArray();
            _results.Clear();
            _cache.Search(query, _results);
            if (!_results.Order().SequenceEqual(expected))
                throw new InvalidOperationException("Cache returned incorrect entries.");
        }
        // The cache must invalidate old hits when the index changes.
        Rectangle inserted = distinct[0];
        _cache.Insert(inserted, -1);
        _results.Clear();
        _cache.Search(inserted, _results);
        if (!_results.Contains(-1)) throw new InvalidOperationException("Cache failed to invalidate after insert.");
        _cache = new RecentQueryCache();
        _cache.BulkLoad(entries);
    }

    [Benchmark(Baseline = true)]
    public int Tree()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _tree.Search(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int Cache4()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _cache.Search(query, _results);
        }
        return total;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class OutputStorageBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    private Rectangle[] _queries = null!;
    private RTree<int> _tree = null!;
    private List<int> _reused = null!;

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        SpatialEntry<int>[] entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            entries[i] = new SpatialEntry<int>(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        _queries = new Rectangle[64];
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            double width = i % 4 switch { 0 => 0, 1 => 20, 2 => 200, _ => 1000 };
            _queries[i] = new Rectangle(x, y, x + width, y + width);
        }
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _reused = new List<int>(Size);
        int expected = _queries.Sum(query => _tree.Search(query).Count);
        if (DefaultAllocating() != expected || FullCapacityAllocating() != expected || ReusedCapacity() != expected)
            throw new InvalidOperationException("Output storage candidates differ.");
    }

    [Benchmark(Baseline = true)]
    public int DefaultAllocating()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
            total += _tree.Search(query).Count;
        return total;
    }

    [Benchmark]
    public int FullCapacityAllocating()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            List<int> result = new(Size);
            total += _tree.Search(query, result);
        }
        return total;
    }

    [Benchmark]
    public int ReusedCapacity()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _reused.Clear();
            total += _tree.Search(query, _reused);
        }
        return total;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class IndexBuildBenchmarks
{
    [Params(32, 256, 1_000, 10_000)] public int Size { get; set; }
    private Rectangle[] _bounds = null!;
    private SpatialEntry<int>[] _entries = null!;

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _bounds = new Rectangle[Size];
        _entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _bounds[i] = new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            _entries[i] = new SpatialEntry<int>(_bounds[i], i);
        }
    }

    [Benchmark(Baseline = true)]
    public object PackedTree()
    {
        RTree<int> tree = new();
        tree.BulkLoad(_entries);
        return tree;
    }

    [Benchmark]
    public object LinearIndex() => new LinearIndex(_bounds);
}

[ShortRunJob]
[MemoryDiagnoser]
public class ByteSpanBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    [Params("Point", "Broad")] public string QueryWidth { get; set; } = "Point";
    private Rectangle[] _bounds = null!;
    private Rectangle[] _queries = null!;
    private byte[] _bytes = null!;
    private byte[] _unaligned = null!;
    private LinearIndex _linear = null!;
    private readonly List<int> _results = [];

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _bounds = new Rectangle[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _bounds[i] = new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
        }
        _queries = new Rectangle[64];
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            double width = QueryWidth == "Point" ? 0 : 1000;
            _queries[i] = new Rectangle(x, y, x + width, y + width);
        }
        _bytes = new byte[ByteSpanScan.RequiredBytes(Size)];
        _unaligned = new byte[_bytes.Length + 1];
        ByteSpanScan.Fill(_bounds, _bytes);
        ByteSpanScan.Fill(_bounds, _unaligned.AsSpan(1));
        _linear = new LinearIndex(_bounds);
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            _linear.Simd(query, _results);
            int[] expected = _results.ToArray();
            _results.Clear();
            _linear.SimdByRef(query, _results);
            if (!_results.SequenceEqual(expected)) throw new InvalidOperationException("Byref array scan differs.");
            _results.Clear();
            ByteSpanScan.Search(_bytes, Size, query, _results);
            if (!_results.SequenceEqual(expected)) throw new InvalidOperationException("Byte-span scan differs.");
            _results.Clear();
            ByteSpanScan.Search(_unaligned.AsSpan(1), Size, query, _results);
            if (!_results.SequenceEqual(expected)) throw new InvalidOperationException("Unaligned byte-span scan differs.");
        }
    }

    [Benchmark(Baseline = true)]
    public int SoaArrays()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _linear.Simd(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int SoaByRef()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _linear.SimdByRef(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int ByteSpan()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += ByteSpanScan.Search(_bytes, Size, query, _results);
        }
        return total;
    }

    [Benchmark]
    public int ByteSpanOffsetOne()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += ByteSpanScan.Search(_unaligned.AsSpan(1), Size, query, _results);
        }
        return total;
    }

    [Benchmark]
    public object BuildBytes()
    {
        byte[] storage = new byte[ByteSpanScan.RequiredBytes(Size)];
        ByteSpanScan.Fill(_bounds, storage);
        return storage;
    }

    [Benchmark]
    public int PopulateProvidedBytes()
    {
        ByteSpanScan.Fill(_bounds, _bytes);
        return _bytes.Length;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class WorkspaceBuildBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    private SpatialEntry<int>[] _entries = null!;
    private BulkLoadWorkspace _workspace = null!;

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _entries[i] = new SpatialEntry<int>(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        _workspace = new BulkLoadWorkspace(Size);
        RTree<int> reference = new();
        reference.BulkLoad(_entries);
        RTree<int> candidate = new();
        candidate.BulkLoad(_entries, _workspace);
        for (int i = 0; i < 64; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            Rectangle query = new(x, y, x + 200, y + 200);
            if (!candidate.Search(query).Order().SequenceEqual(reference.Search(query).Order()))
                throw new InvalidOperationException("Workspace build differs from default build.");
        }
    }

    [Benchmark(Baseline = true)]
    public object Default()
    {
        RTree<int> tree = new();
        tree.BulkLoad(_entries);
        return tree;
    }

    [Benchmark]
    public object FreshWorkspace()
    {
        RTree<int> tree = new();
        tree.BulkLoad(_entries, new BulkLoadWorkspace(Size));
        return tree;
    }

    [Benchmark]
    public object ReusedWorkspace()
    {
        RTree<int> tree = new();
        tree.BulkLoad(_entries, _workspace);
        return tree;
    }
}

internal static class HypothesisValidation
{
    internal static void Run()
    {
        foreach (int count in new[] { 0, 1, 2, 3, 4, 5, 31, 33, 63, 65, 1001 })
        {
            Random random = new(9000 + count);
            Rectangle[] bounds = new Rectangle[count];
            for (int i = 0; i < count; i++)
            {
                double x = random.NextDouble() * 100;
                double y = random.NextDouble() * 100;
                bounds[i] = new Rectangle(x, y, x + 1 + random.NextDouble() * 8, y + 1 + random.NextDouble() * 8);
            }
            LinearIndex index = new(bounds);
            byte[] bytes = new byte[ByteSpanScan.RequiredBytes(count) + 1];
            ByteSpanScan.Fill(bounds, bytes.AsSpan(1));
            List<int> result = [];
            for (int q = 0; q < 100; q++)
            {
                Rectangle query = q < count
                    ? new Rectangle(bounds[q].MaxX, bounds[q].MaxY, bounds[q].MaxX, bounds[q].MaxY)
                    : new Rectangle(random.NextDouble() * 100, random.NextDouble() * 100, 100, 100);
                int[] expected = Enumerable.Range(0, count).Where(i => bounds[i].Intersects(query)).ToArray();
                foreach (Func<Rectangle, List<int>, int> search in new Func<Rectangle, List<int>, int>[]
                         { index.Scalar, index.Simd, index.SimdByRef, index.Bitmap, index.OneBitmap, (r, output) => ByteSpanScan.Search(bytes.AsSpan(1), count, r, output) })
                {
                    result.Clear();
                    if (search(query, result) != expected.Length || !result.SequenceEqual(expected))
                        throw new InvalidOperationException($"Scan mismatch at count={count}, query={q}.");
                }
            }
        }
        Console.WriteLine("Experimental scan, bitmap, byte-span, tail, and edge-contact checks passed.");
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class CrossoverBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    [Params(20, 200, 500, 1_000)] public int Width { get; set; }

    private Rectangle[] _queries = null!;
    private RTree<int> _tree = null!;
    private LinearIndex _linear = null!;
    private readonly List<int> _results = [];

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        Rectangle[] bounds = new Rectangle[Size];
        SpatialEntry<int>[] entries = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            bounds[i] = new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            entries[i] = new SpatialEntry<int>(bounds[i], i);
        }
        _queries = new Rectangle[64];
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _queries[i] = new Rectangle(x, y, x + Width, y + Width);
        }
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _linear = new LinearIndex(bounds);
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            _tree.Search(query, _results);
            int[] expected = _results.Order().ToArray();
            _results.Clear();
            _linear.OneBitmap(query, _results);
            if (!_results.Order().SequenceEqual(expected))
                throw new InvalidOperationException("Crossover candidate returned incorrect entries.");
        }
    }

    [Benchmark(Baseline = true)]
    public int PackedTree()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _tree.Search(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int OneBitmap()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _linear.OneBitmap(query, _results);
        }
        return total;
    }
}
