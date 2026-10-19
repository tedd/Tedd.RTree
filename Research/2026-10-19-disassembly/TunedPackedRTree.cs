using System.Runtime.Intrinsics;
using System.Runtime.Intrinsics.X86;
using System.Runtime.CompilerServices;

namespace Tedd.RTree;

/// <summary>An immutable, packed two-dimensional spatial index with double coordinates.</summary>
/// <remarks>Construction copies entries into owned storage. Concurrent searches require separate result lists.
/// An optional workspace is exclusive scratch storage during construction and is not retained.</remarks>
/// <typeparam name="T">The indexed value type.</typeparam>
public sealed class PackedRTree<T> : IReadOnlySpatialIndex<Rectangle, T>
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
    public PackedRTree(IReadOnlyList<SpatialEntry<T>> items, int maxEntries = 16,
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
        PackedKeyEncoding.Fill(source, keys, order, minX, minY, width, height, scaleX, scaleY);
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

    // Keep recursive traversal from expanding into its callers under profile-guided inlining.
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining | System.Runtime.CompilerServices.MethodImplOptions.AggressiveOptimization)]
    private int SearchLevel(int level, int start, int end, in Rectangle bounds, List<T> results)
    {
        ReadOnlySpan<Rectangle> boxes = _boxes.AsSpan(start, end - start);
        int found = 0;
        if (level == 0)
        {
            if (Avx.IsSupported)
            {
                var q = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in bounds)));
                var mask = Vector256.Create(-1L).AsDouble();
                for (int j = 0; j < boxes.Length; j++)
                {
                    var b = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle, double>(ref Unsafe.AsRef(in boxes[j])));
                    var left = Avx.InsertVector128(b, q.GetLower(), 1);
                    var right = Avx.Permute2x128(q, b, 0x31);
                    var match = Avx.Compare(right, left, FloatComparisonMode.UnorderedNotLessThanSignaling);
                    if (Avx.TestC(match, mask)) { results.Add(_values[start + j]); found++; }
                }
            }
            else
            {
                for (int j = 0; j < boxes.Length; j++)
                    if (boxes[j].Intersects(bounds)) { results.Add(_values[start + j]); found++; }
            }
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
