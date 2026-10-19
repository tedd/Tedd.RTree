using System.Runtime.Intrinsics;

namespace Tedd.RTree;

/// <summary>An immutable, packed two-dimensional spatial index with double coordinates.</summary>
/// <remarks>Construction copies entries into owned storage. Concurrent searches require separate result lists.
/// An optional workspace is exclusive scratch storage during construction and is not retained.</remarks>
/// <typeparam name="T">The indexed value type.</typeparam>
public sealed class NormalizedScalarPackedRTree<T> : IReadOnlySpatialIndex<Rectangle, T>
{
    private readonly Vector256<double>[] _boxes;
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
    public NormalizedScalarPackedRTree(IReadOnlyList<SpatialEntry<T>> items, int maxEntries = 16,
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
        KeyEncoding.Fill(source, keys, order, minX, minY, width, height, scaleX, scaleY);
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
        _boxes = new Vector256<double>[total];
        _values = new T[Count];
        for (int i = 0; i < Count; i++)
        {
            SpatialEntry<T> entry = source[order[i]];
            _boxes[i] = EncodeBounds(entry.Bounds);
            _values[i] = entry.Item;
        }
        for(int level=1;level<levels;level++)
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

    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Overlaps(in Vector256<double> b,in Vector256<double> q)=>b.GetElement(0)<=q.GetElement(0)&&b.GetElement(2)<=q.GetElement(2)&&b.GetElement(1)<=q.GetElement(1)&&b.GetElement(3)<=q.GetElement(3);
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.AggressiveInlining)]
    private static bool Contains(in Vector256<double> b,in Vector256<double> q)=>b.GetElement(0)>=q.GetElement(0)&&b.GetElement(1)>=q.GetElement(1)&&b.GetElement(2)>=q.GetElement(2)&&b.GetElement(3)>=q.GetElement(3);

    /// <inheritdoc/>
    public int Search(Rectangle bounds, List<T> results)
    {
        ArgumentNullException.ThrowIfNull(results);
        if (Count == 0 || !_extent.Intersects(bounds)) return 0;
        if (bounds.Contains(_extent)) { results.AddRange(_values.AsSpan()); return Count; }
        int level = _starts.Length - 1;
        var overlap=Vector256.Create(bounds.MaxX,bounds.MaxY,-bounds.MinX,-bounds.MinY);
        var contained=EncodeBounds(bounds);
        return SearchLevel(level,_starts[level],_boxes.Length,overlap,contained,results);
    }

    private int SearchLevel(int level, int start, int end, in Vector256<double> overlap, in Vector256<double> contained, List<T> results)
    {
        ReadOnlySpan<Vector256<double>> boxes = _boxes.AsSpan(start, end - start);
        int found = 0;
        if (level == 0)
        {
            for (int j = 0; j < boxes.Length; j++)
                if (Overlaps(boxes[j],overlap)) { results.Add(_values[start + j]); found++; }
        }
        else
        {
            int lowerStart = _starts[level - 1], lowerEnd = _starts[level];
            for (int j = 0; j < boxes.Length; j++)
            {
                ref readonly Vector256<double> box = ref boxes[j];
                if (!Overlaps(box,overlap)) continue;
                int local = start + j - lowerEnd;
                if (Contains(box,contained))
                {
                    int first = local * _spans[level];
                    int count = Math.Min(_spans[level], Count - first);
                    results.AddRange(_values.AsSpan(first, count));
                    found += count;
                }
                else
                {
                    int first = lowerStart + local * _capacity;
                    found += SearchLevel(level - 1, first, first + Math.Min(_capacity, lowerEnd - first), overlap, contained, results);
                }
            }
        }
        return found;
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
