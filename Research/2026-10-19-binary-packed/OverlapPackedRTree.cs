using System.Runtime.Intrinsics;

namespace Tedd.RTree;

/// <summary>An immutable, packed two-dimensional spatial index with double coordinates.</summary>
/// <remarks>Construction copies entries into owned storage. Concurrent searches require separate result lists.
/// An optional workspace is exclusive scratch storage during construction and is not retained.</remarks>
/// <typeparam name="T">The indexed value type.</typeparam>
public sealed class OverlapPackedRTree<T> : IReadOnlySpatialIndex<Rectangle, T>
{
    private readonly Rectangle[] _boxes;
    private readonly T[] _values;
    private readonly int[] _starts, _spans;
    private readonly int _capacity;
    private readonly Rectangle _extent;
    /// <summary>Gets the number of indexed entries, including duplicates.</summary>
    public int Count { get; }

    /// <summary>Builds an immutable index from the supplied entries.</summary>
    /// <param name="items">Entries to copy; duplicates are retained.</param>
    /// <param name="maxEntries">Maximum entries per node, from 4 through 128.</param>
    /// <param name="workspace">Optional exclusive scratch space, reusable after construction.</param>
    public OverlapPackedRTree(IReadOnlyList<SpatialEntry<T>> items, int maxEntries = 16,
        BulkLoadWorkspace? workspace = null)
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
        Span<uint> xs = stackalloc uint[8], ys = stackalloc uint[8];
        int vectorCount = Vector256.IsHardwareAccelerated ? Count & ~7 : 0;
        for (int first = 0; first < vectorCount; first += 8)
        {
            for (int lane = 0; lane < 8; lane++)
            {
                int index = first + lane;
            Rectangle b = source[index].Bounds;
            double x = (b.MinX * 0.25 + b.MaxX * 0.25 - minX);
            double y = (b.MinY * 0.25 + b.MaxY * 0.25 - minY);
            // Sort-key rounding cannot change stored bounds or intersection semantics. Retain
            // division for subnormal extents whose reciprocal scale cannot be represented.
            uint ix = width > 0 ? (uint)Math.Clamp(finiteX ? x * scaleX : x / width * 65535, 0, 65535) : 0;
            uint iy = height > 0 ? (uint)Math.Clamp(finiteY ? y * scaleY : y / height * 65535, 0, 65535) : 0;
            xs[lane] = ix; ys[lane] = iy;
            order[index] = index;
            }
            HilbertOrder.Encode(Vector256.Create(xs), Vector256.Create(ys)).CopyTo(keys.Slice(first, 8));
        }
        for (int i = vectorCount; i < Count; i++)
        {
            Rectangle b = source[i].Bounds;
            double x = (b.MinX * 0.25 + b.MaxX * 0.25 - minX);
            double y = (b.MinY * 0.25 + b.MaxY * 0.25 - minY);
            // Sort-key rounding cannot change stored bounds or intersection semantics. Retain
            // division for subnormal extents whose reciprocal scale cannot be represented.
            uint ix = width > 0 ? (uint)Math.Clamp(finiteX ? x * scaleX : x / width * 65535, 0, 65535) : 0;
            uint iy = height > 0 ? (uint)Math.Clamp(finiteY ? y * scaleY : y / height * 65535, 0, 65535) : 0;
            keys[i] = HilbertOrder.Encode(ix, iy);
            order[i] = i;
        }
        if (Count < 2048) keys.Sort(order);
        else
        {
            Span<int> scratch = workspace is null ? new int[Count] : workspace.HilbertScatter(Count);
            HilbertOrder.SortIndices(keys, order, scratch);
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

    /// <inheritdoc/>
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
        int initialCount = results.Count;
        // Only a suspended parent is stored. Scratch is O(tree height), not O(fanout*height).
        Span<int> stack = stackalloc int[_starts.Length * 3];
        int depth = 0;
    NextNode:
        if (level == 0)
        {
            for (int i = start; i < end; i++)
                if (_boxes[i].Intersects(bounds)) results.Add(_values[i]);
        }
        else
        {
            int lowerStart = _starts[level - 1], lowerEnd = _starts[level];
            for (int i = start; i < end; i++)
            {
                ref readonly Rectangle box = ref _boxes[i];
                if (!box.Intersects(bounds)) continue;
                int local = i - lowerEnd;
                stack[depth++] = i + 1;
                stack[depth++] = end;
                stack[depth++] = level;
                start = lowerStart + local * _capacity;
                end = start + Math.Min(_capacity, lowerEnd - start);
                level--;
                goto NextNode;
            }
        }
        if (depth == 0) return results.Count - initialCount;
        level = stack[--depth];
        end = stack[--depth];
        start = stack[--depth];
        goto NextNode;
    }

    /// <inheritdoc/>
    public List<T> Search(Rectangle bounds) { List<T> results = []; Search(bounds, results); return results; }

    /// <inheritdoc/>
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
