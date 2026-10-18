namespace Tedd.RTree;

/// <summary>A mutable two-dimensional R-tree with incremental updates and packed bulk loading.</summary>
/// <remarks>Concurrent searches are safe while the tree is unchanged, provided each search owns its result list. Mutation during a search is not safe.</remarks>
public sealed class RTree<T>
{
    private sealed class Node(bool leaf, int capacity)
    {
        // Leaves never carry child references; branches never carry user values.
        internal readonly Rectangle[] Boxes = new Rectangle[capacity + 1];
        internal readonly T[]? Values = leaf ? new T[capacity + 1] : null;
        internal readonly Node?[]? Children = leaf ? null : new Node?[capacity + 1];
        internal readonly bool Leaf = leaf;
        internal int Count;
        internal Rectangle Bounds;
    }

    private struct Entry(Rectangle bounds, Node? child, T value)
    {
        internal Rectangle Bounds = bounds;
        internal Node? Child = child;
        internal T Value = value;
    }

    private readonly int _capacity;
    private readonly int _minimum;
    private Node _root;
    private List<Entry>? _reinsertScratch;

    /// <param name="maxEntries">Maximum entries per node, from 4 to 128.</param>
    public RTree(int maxEntries = 16)
    {
        if (maxEntries is < 4 or > 128)
            throw new ArgumentOutOfRangeException(nameof(maxEntries));

        _capacity = maxEntries;
        _minimum = maxEntries / 2;
        _root = new Node(true, maxEntries);
    }

    /// <summary>Number of indexed items.</summary>
    public int Count { get; private set; }

    /// <summary>Inserts an item. Duplicate items and rectangles are permitted.</summary>
    public void Insert(Rectangle bounds, T item)
    {
        InsertEntry(new Entry(bounds, null, item));
        Count++;
    }

    private void InsertEntry(Entry entry)
    {
        Insert(_root, entry, out Node? sibling);
        if (sibling is not null)
        {
            Node oldRoot = _root;
            Node newRoot = new(false, _capacity);
            Add(newRoot, new Entry(oldRoot.Bounds, oldRoot, default!));
            Add(newRoot, new Entry(sibling.Bounds, sibling, default!));
            _root = newRoot;
        }
    }

    /// <summary>Removes one entry matching both its bounds and value.</summary>
    /// <returns>Whether a matching entry was found.</returns>
    public bool Remove(Rectangle bounds, T item)
    {
        if (Count == 0 || !_root.Bounds.Contains(bounds)) return false;
        List<Entry> reinserts = _reinsertScratch ??= [];
        try
        {
            if (!Remove(_root, bounds, item, reinserts)) return false;
            Count--;
            while (!_root.Leaf && _root.Count == 1)
                _root = _root.Children![0]!;
            if (_root.Count == 0)
                _root = new Node(true, _capacity);
            foreach (Entry entry in reinserts)
                InsertEntry(entry);
            if (Count == 0) _reinsertScratch = null;
            return true;
        }
        finally { reinserts.Clear(); }
    }

    /// <summary>Moves one matching entry to new bounds.</summary>
    /// <returns>Whether a matching entry was found and moved.</returns>
    public bool Update(Rectangle oldBounds, T item, Rectangle newBounds)
    {
        if (!Remove(oldBounds, item)) return false;
        Insert(newBounds, item);
        return true;
    }

    /// <summary>Builds a packed tree from a batch. The tree must be empty; later individual updates are allowed.</summary>
    /// <remarks>Uses Hilbert ordering and bottom-up packing. Input order is not modified.</remarks>
    public void BulkLoad(IReadOnlyList<SpatialEntry<T>> items)
        => BulkLoadCore(items, null);

    /// <summary>Builds a packed tree using caller-owned reusable scratch arrays.</summary>
    /// <remarks>The tree must be empty. Do not use the workspace concurrently with another bulk load.</remarks>
    public void BulkLoad(IReadOnlyList<SpatialEntry<T>> items, BulkLoadWorkspace workspace)
    {
        ArgumentNullException.ThrowIfNull(workspace);
        BulkLoadCore(items, workspace);
    }

    private void BulkLoadCore(IReadOnlyList<SpatialEntry<T>> items, BulkLoadWorkspace? workspace)
    {
        ArgumentNullException.ThrowIfNull(items);
        if (Count != 0)
            throw new InvalidOperationException("Bulk loading requires an empty tree.");
        int itemCount = items.Count;
        if (itemCount == 0)
            return;

        if (items is SpatialEntry<T>[] array)
        {
            BulkLoadPacked(array, workspace);
        }
        else
        {
            // Retain IReadOnlyList's indexed contract, including custom lists without enumeration.
            SpatialEntry<T>[] copy = new SpatialEntry<T>[itemCount];
            for (int i = 0; i < copy.Length; i++) copy[i] = items[i];
            BulkLoadPacked(copy, workspace);
        }
    }

    private void BulkLoadPacked(ReadOnlySpan<SpatialEntry<T>> items, BulkLoadWorkspace? workspace)
    {
        int itemCount = items.Length;
        workspace?.EnsureCapacity(itemCount);
        Span<int> order = workspace is null ? new int[itemCount] : workspace.Order.AsSpan(0, itemCount);
        Span<uint> keys = workspace is null ? new uint[itemCount] : workspace.HilbertKeys(itemCount);
        Rectangle extent = items[0].Bounds;
        for (int i = 0; i < itemCount; i++)
            extent = Rectangle.Union(extent, items[i].Bounds);
        // Halving before subtraction keeps the normalization finite even for [-MaxValue, MaxValue].
        double minX = extent.MinX * 0.5, minY = extent.MinY * 0.5;
        double width = extent.MaxX * 0.5 - minX, height = extent.MaxY * 0.5 - minY;
        double scaleX = width > 0 ? 65535 / width : 0, scaleY = height > 0 ? 65535 / height : 0;
        bool finiteScaleX = double.IsFinite(scaleX), finiteScaleY = double.IsFinite(scaleY);
        for (int i = 0; i < itemCount; i++)
        {
            Rectangle b = items[i].Bounds;
            double x = (b.MinX * 0.25 + b.MaxX * 0.25 - minX);
            double y = (b.MinY * 0.25 + b.MaxY * 0.25 - minY);
            // Sort-key rounding cannot change stored bounds or intersection semantics. Retain
            // division for subnormal extents whose reciprocal scale cannot be represented.
            uint ix = width > 0 ? (uint)Math.Clamp(finiteScaleX ? x * scaleX : x / width * 65535, 0, 65535) : 0;
            uint iy = height > 0 ? (uint)Math.Clamp(finiteScaleY ? y * scaleY : y / height * 65535, 0, 65535) : 0;
            keys[i] = HilbertOrder.Encode(ix, iy);
            order[i] = i;
        }
        // Primitive keys avoid virtual comparisons through an indirect coordinate lookup.
        if (itemCount < 2048)
            keys.Sort(order);
        else
        {
            Span<int> scatter = workspace is null ? new int[itemCount] : workspace.HilbertScatter(itemCount);
            HilbertOrder.SortIndices(keys, order, scatter);
        }
        Node[] level = new Node[(itemCount - 1) / _capacity + 1];
        for (int n = 0, start = 0; n < level.Length; n++, start += _capacity)
        {
            Node node = new(true, _capacity);
            int end = Math.Min(start + _capacity, itemCount);
            for (int i = start; i < end; i++)
            {
                SpatialEntry<T> item = items[order[i]];
                Add(node, new Entry(item.Bounds, null, item.Item));
            }
            level[n] = node;
        }
        while (level.Length > 1)
        {
            Node[] parents = new Node[(level.Length - 1) / _capacity + 1];
            for (int n = 0, start = 0; n < parents.Length; n++, start += _capacity)
            {
                Node parent = new(false, _capacity);
                int end = Math.Min(start + _capacity, level.Length);
                for (int i = start; i < end; i++)
                    Add(parent, new Entry(level[i].Bounds, level[i], default!));
                parents[n] = parent;
            }
            level = parents;
        }
        _root = level[0];
        Count = itemCount;
    }

    /// <summary>Appends intersecting items to <paramref name="results"/> and returns the number appended.</summary>
    public int Search(Rectangle bounds, List<T> results)
    {
        ArgumentNullException.ThrowIfNull(results);
        if (_root.Count == 0 || !_root.Bounds.Intersects(bounds))
            return 0;
        return Search(_root, bounds, results);
    }

    /// <summary>Appends matches for each query to its result list and writes the appended counts.</summary>
    /// <returns>The total number of matches appended across all queries.</returns>
    /// <remarks>
    /// Results must have one non-null list per query; counts must have at least one slot per query.
    /// Existing list contents are preserved. Inputs and output storage must not be changed concurrently.
    /// The tree must not be mutated while the batch runs.
    /// </remarks>
    public long SearchBatch(ReadOnlySpan<Rectangle> queries, ReadOnlySpan<List<T>> results, Span<int> counts)
    {
        if (results.Length != queries.Length)
            throw new ArgumentException("Provide one result list per query.", nameof(results));
        if (counts.Length < queries.Length)
            throw new ArgumentException("Provide at least one count slot per query.", nameof(counts));
        // Validate the entire batch before appending, including lists belonging to empty queries.
        for (int i = 0; i < results.Length; i++)
            if (results[i] is null)
                throw new ArgumentException("Result lists must not be null.", nameof(results));
        long total = 0;
        for (int i = 0; i < queries.Length; i++)
        {
            int found = Search(queries[i], results[i]);
            counts[i] = found;
            total += found;
        }
        return total;
    }

    /// <summary>Returns a new list containing items whose bounds intersect <paramref name="bounds"/>.</summary>
    public List<T> Search(Rectangle bounds)
    {
        List<T> results = [];
        Search(bounds, results);
        return results;
    }

    /// <summary>Removes all indexed items.</summary>
    public void Clear()
    {
        _root = new Node(true, _capacity);
        Count = 0;
        _reinsertScratch = null;
    }

    private static int CollectValues(Node node, List<T> results)
    {
        if (node.Leaf)
        {
            results.AddRange(node.Values!.AsSpan(0, node.Count));
            return node.Count;
        }
        int found = 0;
        for (int i = 0; i < node.Count; i++) found += CollectValues(node.Children![i]!, results);
        return found;
    }

    private static int Search(Node node, in Rectangle bounds, List<T> results)
    {
        // Validate the active prefix once; mutations cannot overlap a search (H-004/H-014).
        ReadOnlySpan<Rectangle> entries = node.Boxes.AsSpan(0, node.Count);
        int found = 0;
        if (node.Leaf)
        {
            for (int i = 0; i < entries.Length; i++)
            {
                ref readonly Rectangle entry = ref entries[i];
                if (entry.Intersects(bounds))
                {
                    results.Add(node.Values![i]);
                    found++;
                }
            }
        }
        else
        {
            for (int i = 0; i < entries.Length; i++)
            {
                ref readonly Rectangle entry = ref entries[i];
                if (entry.Intersects(bounds))
                {
                    // Every descendant lies within this entry. Containment therefore permits
                    // collecting values without further geometry tests, preserving duplicates.
                    // Check only intersecting children to limit selective-query overhead (H-013/H-014).
                    found += bounds.Contains(entry)
                        ? CollectValues(node.Children![i]!, results)
                        : Search(node.Children![i]!, bounds, results);
                }
            }
        }
        return found;
    }

    private bool Remove(Node node, in Rectangle bounds, T item, List<Entry> reinserts)
    {
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++)
            {
                Entry entry = ReadEntry(node, i);
                if (entry.Bounds != bounds || !EqualityComparer<T>.Default.Equals(entry.Value, item)) continue;
                RemoveAt(node, i);
                RecomputeBounds(node);
                return true;
            }
            return false;
        }

        for (int i = 0; i < node.Count; i++)
        {
            if (!node.Boxes[i].Contains(bounds)) continue;
            Node child = node.Children![i]!;
            if (!Remove(child, bounds, item, reinserts)) continue;
            if (child.Count < _minimum)
            {
                CollectLeafEntries(child, reinserts);
                RemoveAt(node, i);
            }
            else
                node.Boxes[i] = child.Bounds;
            RecomputeBounds(node);
            return true;
        }
        return false;
    }

    private static void RemoveAt(Node node, int index)
    {
        int last = --node.Count;
        if (index != last)
        {
            node.Boxes[index] = node.Boxes[last];
            if (node.Leaf) node.Values![index] = node.Values[last];
            else node.Children![index] = node.Children[last];
        }
        node.Boxes[last] = default;
        if (node.Leaf) node.Values![last] = default!;
        else node.Children![last] = null;
    }

    private static void RecomputeBounds(Node node)
    {
        if (node.Count == 0)
        {
            node.Bounds = default;
            return;
        }
        Rectangle bounds = node.Boxes[0];
        for (int i = 1; i < node.Count; i++)
            bounds = Rectangle.Union(bounds, node.Boxes[i]);
        node.Bounds = bounds;
    }

    private static void CollectLeafEntries(Node node, List<Entry> entries)
    {
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++) entries.Add(ReadEntry(node, i));
        }
        else
        {
            for (int i = 0; i < node.Count; i++) CollectLeafEntries(node.Children![i]!, entries);
        }
    }

    private void Insert(Node node, Entry entry, out Node? sibling)
    {
        if (node.Leaf)
        {
            Add(node, entry);
        }
        else
        {
            int selected = ChooseSubtree(node, entry.Bounds);
            Node child = node.Children![selected]!;
            Insert(child, entry, out Node? childSibling);
            node.Boxes[selected] = child.Bounds;
            node.Bounds = Rectangle.Union(node.Bounds, child.Bounds);
            if (childSibling is not null)
                Add(node, new Entry(childSibling.Bounds, childSibling, default!));
        }

        sibling = node.Count > _capacity ? Split(node) : null;
    }

    private static int ChooseSubtree(Node node, in Rectangle bounds)
    {
        int best = 0;
        double bestEnlargement = double.MaxValue;
        double bestArea = double.MaxValue;
        for (int i = 0; i < node.Count; i++)
        {
            Rectangle current = node.Boxes[i];
            double area = current.Area;
            double enlargement = Enlargement(current, bounds, area);
            if (enlargement < bestEnlargement ||
                (enlargement == bestEnlargement && area < bestArea))
            {
                best = i;
                bestEnlargement = enlargement;
                bestArea = area;
            }
        }
        return best;
    }

    private Node Split(Node node)
    {
        int length = node.Count;
        Entry[] entries = new Entry[length];
        Span<double> entryAreas = stackalloc double[length];
        for (int i = 0; i < length; i++)
        {
            entries[i] = ReadEntry(node, i);
            entryAreas[i] = entries[i].Bounds.Area;
        }
        int seedA = 0, seedB = 1;
        double worstWaste = double.NegativeInfinity;
        for (int i = 0; i < length - 1; i++)
        {
            for (int j = i + 1; j < length; j++)
            {
                double waste = Rectangle.Union(entries[i].Bounds, entries[j].Bounds).Area -
                    entryAreas[i] - entryAreas[j];
                if (waste > worstWaste)
                {
                    worstWaste = waste;
                    seedA = i;
                    seedB = j;
                }
            }
        }

        Node other = new(node.Leaf, _capacity);
        bool[] assigned = new bool[length];
        Entry first = entries[seedA], second = entries[seedB];
        node.Count = 0;
        Add(node, first);
        Add(other, second);
        assigned[seedA] = assigned[seedB] = true;
        int remaining = length - 2;

        while (remaining > 0)
        {
            if (node.Count + remaining == _minimum || other.Count + remaining == _minimum)
            {
                Node target = node.Count + remaining == _minimum ? node : other;
                for (int i = 0; i < length; i++)
                    if (!assigned[i]) Add(target, entries[i]);
                break;
            }

            int selected = -1;
            double greatestDifference = double.NegativeInfinity;
            double areaA = node.Bounds.Area, areaB = other.Bounds.Area;
            double enlargementA = 0, enlargementB = 0;
            for (int i = 0; i < length; i++)
            {
                if (assigned[i]) continue;
                double a = Enlargement(node.Bounds, entries[i].Bounds, areaA);
                double b = Enlargement(other.Bounds, entries[i].Bounds, areaB);
                double difference = Math.Abs(a - b);
                if (difference > greatestDifference)
                {
                    greatestDifference = difference;
                    selected = i;
                    enlargementA = a;
                    enlargementB = b;
                }
            }

            Node destination = enlargementA < enlargementB ? node :
                enlargementB < enlargementA ? other :
                areaA < areaB ? node :
                areaB < areaA ? other :
                node.Count <= other.Count ? node : other;
            Add(destination, entries[selected]);
            assigned[selected] = true;
            remaining--;
        }
        // The vacated slots otherwise retain values and child nodes after a split.
        Array.Clear(node.Boxes, node.Count, length - node.Count);
        if (node.Leaf) Array.Clear(node.Values!, node.Count, length - node.Count);
        else Array.Clear(node.Children!, node.Count, length - node.Count);
        return other;
    }

    private static double Enlargement(in Rectangle current, in Rectangle added, double before)
    {
        double after = Rectangle.Union(current, added).Area;
        return after > before ? after - before : 0;
    }

    private static void Add(Node node, Entry entry)
    {
        int index = node.Count++;
        node.Boxes[index] = entry.Bounds;
        if (node.Leaf) node.Values![index] = entry.Value;
        else node.Children![index] = entry.Child;
        node.Bounds = node.Count == 1 ? entry.Bounds : Rectangle.Union(node.Bounds, entry.Bounds);
    }

    private static Entry ReadEntry(Node node, int index) =>
        new(node.Boxes[index], node.Leaf ? null : node.Children![index], node.Leaf ? node.Values![index] : default!);

}
