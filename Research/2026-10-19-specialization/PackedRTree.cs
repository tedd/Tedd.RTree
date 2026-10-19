namespace Tedd.RTree;

/// <summary>Research prototype: immutable flat 2D index with owned storage.</summary>
public sealed class PackedRTree<T> : IReadOnlySpatialIndex<Rectangle, T>
{
    private readonly Rectangle[] _boxes;
    private readonly T[] _values;
    private readonly int[] _starts, _spans;
    private readonly int _capacity;
    private readonly Rectangle _extent;
    public int Count { get; }

    public PackedRTree(IReadOnlyList<SpatialEntry<T>> items, int maxEntries = 16,
        bool partial = false, BulkLoadWorkspace? workspace = null)
    {
        ArgumentNullException.ThrowIfNull(items);
        if (maxEntries is < 4 or > 128) throw new ArgumentOutOfRangeException(nameof(maxEntries));
        _capacity = maxEntries;
        Count = items.Count;
        if (Count == 0) { _boxes = []; _values = []; _starts = []; _spans = []; return; }
        SpatialEntry<T>[]? copy = null;
        if (items is not SpatialEntry<T>[])
        {
            copy = new SpatialEntry<T>[Count];
            for (int i = 0; i < copy.Length; i++) copy[i] = items[i];
        }
        ReadOnlySpan<SpatialEntry<T>> source = copy ?? (SpatialEntry<T>[])items;
        workspace?.EnsureCapacity(Count);
        Span<int> order = workspace is null ? new int[Count] : workspace.Order.AsSpan(0, Count);
        Span<uint> keys = workspace is null ? new uint[Count] : workspace.HilbertKeys(Count);
        Rectangle extent = source[0].Bounds;
        for (int i = 1; i < source.Length; i++) extent = Rectangle.Union(extent, source[i].Bounds);
        _extent = extent;
        double minX = extent.MinX * 0.5, minY = extent.MinY * 0.5;
        double width = extent.MaxX * 0.5 - minX, height = extent.MaxY * 0.5 - minY;
        double scaleX = width > 0 ? 65535 / width : 0, scaleY = height > 0 ? 65535 / height : 0;
        bool finiteX = double.IsFinite(scaleX), finiteY = double.IsFinite(scaleY);
        for (int i = 0; i < Count; i++)
        {
            Rectangle b = source[i].Bounds;
            double x = b.MinX * 0.25 + b.MaxX * 0.25 - minX;
            double y = b.MinY * 0.25 + b.MaxY * 0.25 - minY;
            uint ix = width > 0 ? (uint)Math.Clamp(finiteX ? x * scaleX : x / width * 65535, 0, 65535) : 0;
            uint iy = height > 0 ? (uint)Math.Clamp(finiteY ? y * scaleY : y / height * 65535, 0, 65535) : 0;
            keys[i] = HilbertOrder.Encode(ix, iy);
            order[i] = i;
        }
        if (!partial && Count < 2048) keys.Sort(order);
        else
        {
            Span<int> scratch = workspace is null ? new int[Count] : workspace.HilbertScatter(Count);
            if (partial) PartialOrder.Sort(keys, order, scratch, _capacity);
            else HilbertOrder.SortIndices(keys, order, scratch);
        }
        Span<int> starts = stackalloc int[32], spans = stackalloc int[32];
        int levels = 1, total = Count, children = Count, span = 1;
        starts[0] = 0; spans[0] = 1;
        while (children > _capacity)
        {
            starts[levels] = total;
            span = checked(span * _capacity);
            spans[levels++] = span;
            children = (children - 1) / _capacity + 1;
            total = checked(total + children);
        }
        _starts = starts[..levels].ToArray();
        _spans = spans[..levels].ToArray();
        _boxes = new Rectangle[total];
        _values = new T[Count];
        for (int i = 0; i < Count; i++)
        {
            SpatialEntry<T> entry = source[order[i]];
            _boxes[i] = entry.Bounds;
            _values[i] = entry.Item;
        }
        for (int level = 1; level < levels; level++)
        {
            int lowerStart = _starts[level - 1], lowerEnd = _starts[level];
            for (int first = lowerStart, destination = _starts[level]; first < lowerEnd; first += _capacity, destination++)
            {
                int end = first + Math.Min(_capacity, lowerEnd - first);
                Rectangle bounds = _boxes[first];
                for (int i = first + 1; i < end; i++) bounds = Rectangle.Union(bounds, _boxes[i]);
                _boxes[destination] = bounds;
            }
        }
    }

    public int Search(Rectangle bounds, List<T> results)
    {
        ArgumentNullException.ThrowIfNull(results);
        if (Count == 0 || !_extent.Intersects(bounds)) return 0;
        if (bounds.Contains(_extent)) { results.AddRange(_values.AsSpan()); return Count; }
        int level = _starts.Length - 1;
        return SearchLevel(level, _starts[level], _boxes.Length, bounds, results);
    }

    private int SearchLevel(int level, int start, int end, in Rectangle bounds, List<T> results)
    {
        ReadOnlySpan<Rectangle> boxes = _boxes.AsSpan(start, end - start);
        int found = 0;
        if (level == 0)
        {
            for (int j = 0; j < boxes.Length; j++)
                if (boxes[j].Intersects(bounds)) { results.Add(_values[start + j]); found++; }
        }
        else
        {
            int lowerStart = _starts[level - 1], lowerEnd = _starts[level];
            for (int j = 0; j < boxes.Length; j++)
            {
                ref readonly Rectangle box = ref boxes[j];
                if (!box.Intersects(bounds)) continue;
                int local = start + j - lowerEnd;
                if (bounds.Contains(box))
                {
                    int first = local * _spans[level];
                    int count = Math.Min(_spans[level], Count - first);
                    results.AddRange(_values.AsSpan(first, count));
                    found += count;
                }
                else
                {
                    int first = lowerStart + local * _capacity;
                    found += SearchLevel(level - 1, first, first + Math.Min(_capacity, lowerEnd - first), bounds, results);
                }
            }
        }
        return found;
    }

    public List<T> Search(Rectangle bounds) { List<T> results = []; Search(bounds, results); return results; }

    public long SearchBatch(ReadOnlySpan<Rectangle> queries, ReadOnlySpan<List<T>> results, Span<int> counts)
    {
        if (results.Length != queries.Length) throw new ArgumentException("Provide one result list per query.", nameof(results));
        if (counts.Length < queries.Length) throw new ArgumentException("Provide at least one count slot per query.", nameof(counts));
        for (int i = 0; i < results.Length; i++)
            if (results[i] is null) throw new ArgumentException("Result lists must not be null.", nameof(results));
        long found = 0;
        for (int i = 0; i < queries.Length; i++) { counts[i] = Search(queries[i], results[i]); found += counts[i]; }
        return found;
    }
}
