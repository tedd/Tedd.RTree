using System.Numerics;

namespace Tedd.RTree;

/// <summary>A mutable three-dimensional R-tree with incremental updates and packed bulk loading.</summary>
/// <remarks>Concurrent searches are safe while the tree is unchanged, provided each search owns its result list. Mutation during a search is not safe.</remarks>
public sealed class RTree3D<TCoordinate, T>
    where TCoordinate : struct, System.Numerics.INumber<TCoordinate>
{
    private sealed class AxisComparer(double[] centers) : IComparer<int>
    {
        public int Compare(int a, int b) => centers[a].CompareTo(centers[b]);
    }

    private sealed class IntegerAxisComparer(BigInteger[] centers) : IComparer<int>
    {
        public int Compare(int a, int b) => centers[a].CompareTo(centers[b]);
    }

    private sealed class Node(bool leaf, int capacity)
    {
        internal readonly Entry[] Entries = new Entry[capacity + 1];
        internal readonly bool Leaf = leaf;
        internal int Count;
        internal Box<TCoordinate> Bounds;
    }

    private struct Entry(Box<TCoordinate> bounds, Node? child, T value)
    {
        internal Box<TCoordinate> Bounds = bounds;
        internal Node? Child = child;
        internal T Value = value;
    }

    private readonly int _capacity;
    private readonly int _minimum;
    private Node _root;
    private List<Entry>? _reinsertScratch;

    /// <param name="maxEntries">Maximum entries per node, from 4 to 128.</param>
    public RTree3D(int maxEntries = 16)
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
    public void Insert(Box<TCoordinate> bounds, T item)
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
    public bool Remove(Box<TCoordinate> bounds, T item)
    {
        if (Count == 0 || !_root.Bounds.Contains(bounds)) return false;
        List<Entry> reinserts = _reinsertScratch ??= [];
        try
        {
            if (!Remove(_root, bounds, item, reinserts)) return false;
            Count--;
            while (!_root.Leaf && _root.Count == 1)
                _root = _root.Entries[0].Child!;
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
    public bool Update(Box<TCoordinate> oldBounds, T item, Box<TCoordinate> newBounds)
    {
        if (!Remove(oldBounds, item)) return false;
        Insert(newBounds, item);
        return true;
    }

    /// <summary>Builds a packed tree from a batch. The tree must be empty; later individual updates are allowed.</summary>
    /// <remarks>Uses Sort-Tile-Recursive packing. Input order is not modified.</remarks>
    public void BulkLoad(IReadOnlyList<SpatialEntry3D<TCoordinate, T>> items)
        => BulkLoadCore(items, null);

    /// <summary>Builds a packed tree using caller-owned reusable scratch arrays.</summary>
    /// <remarks>The tree must be empty. Do not use the workspace concurrently with another bulk load.</remarks>
    public void BulkLoad(IReadOnlyList<SpatialEntry3D<TCoordinate, T>> items, BulkLoadWorkspace workspace)
    {
        ArgumentNullException.ThrowIfNull(workspace);
        BulkLoadCore(items, workspace);
    }

    private void BulkLoadCore(IReadOnlyList<SpatialEntry3D<TCoordinate, T>> items, BulkLoadWorkspace? workspace)
    {
        ArgumentNullException.ThrowIfNull(items);
        if (Count != 0)
            throw new InvalidOperationException("Bulk loading requires an empty tree.");
        int itemCount = items.Count;
        if (itemCount == 0)
            return;

        Entry[] level = new Entry[itemCount];
        for (int i = 0; i < itemCount; i++)
        {
            SpatialEntry3D<TCoordinate, T> item = items[i];
            level[i] = new Entry(item.Bounds, null, item.Item);
        }

        bool leaf = true;
        while (true)
        {
            Node[] nodes = PackLevel(level, leaf, workspace);
            if (nodes.Length == 1)
            {
                _root = nodes[0];
                Count = itemCount;
                return;
            }

            level = new Entry[nodes.Length];
            for (int i = 0; i < nodes.Length; i++)
                level[i] = new Entry(nodes[i].Bounds, nodes[i], default!);
            leaf = false;
        }
    }

    /// <summary>Appends intersecting items to <paramref name="results"/> and returns the number appended.</summary>
    public int Search(Box<TCoordinate> bounds, List<T> results)
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
    public long SearchBatch(ReadOnlySpan<Box<TCoordinate>> queries, ReadOnlySpan<List<T>> results, Span<int> counts)
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
    public List<T> Search(Box<TCoordinate> bounds)
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

    private static int Search(Node node, in Box<TCoordinate> bounds, List<T> results)
    {
        int found = 0;
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++)
            {
                ref Entry entry = ref node.Entries[i];
                if (entry.Bounds.Intersects(bounds))
                {
                    results.Add(entry.Value);
                    found++;
                }
            }
        }
        else
        {
            for (int i = 0; i < node.Count; i++)
            {
                ref Entry entry = ref node.Entries[i];
                if (entry.Bounds.Intersects(bounds))
                    found += Search(entry.Child!, bounds, results);
            }
        }
        return found;
    }

    private bool Remove(Node node, in Box<TCoordinate> bounds, T item, List<Entry> reinserts)
    {
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++)
            {
                Entry entry = node.Entries[i];
                if (entry.Bounds != bounds || !EqualityComparer<T>.Default.Equals(entry.Value, item)) continue;
                RemoveAt(node, i);
                RecomputeBounds(node);
                return true;
            }
            return false;
        }

        for (int i = 0; i < node.Count; i++)
        {
            ref Entry entry = ref node.Entries[i];
            if (!entry.Bounds.Contains(bounds)) continue;
            Node child = entry.Child!;
            if (!Remove(child, bounds, item, reinserts)) continue;
            if (child.Count < _minimum)
            {
                CollectLeafEntries(child, reinserts);
                RemoveAt(node, i);
            }
            else
                entry.Bounds = child.Bounds;
            RecomputeBounds(node);
            return true;
        }
        return false;
    }

    private static void RemoveAt(Node node, int index)
    {
        int last = --node.Count;
        if (index != last) node.Entries[index] = node.Entries[last];
        node.Entries[last] = default;
    }

    private static void RecomputeBounds(Node node)
    {
        if (node.Count == 0)
        {
            node.Bounds = default;
            return;
        }
        Box<TCoordinate> bounds = node.Entries[0].Bounds;
        for (int i = 1; i < node.Count; i++)
            bounds = Box<TCoordinate>.Union(bounds, node.Entries[i].Bounds);
        node.Bounds = bounds;
    }

    private static void CollectLeafEntries(Node node, List<Entry> entries)
    {
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++) entries.Add(node.Entries[i]);
        }
        else
        {
            for (int i = 0; i < node.Count; i++) CollectLeafEntries(node.Entries[i].Child!, entries);
        }
    }

    private Node[] PackLevel(Entry[] entries, bool leaf, BulkLoadWorkspace? workspace)
    {
        int nodeCount = (entries.Length + _capacity - 1) / _capacity;
        Node[] nodes = new Node[nodeCount];
        int slabs = (int)Math.Ceiling(Math.Cbrt(nodeCount));
        int slabCapacity = ((nodeCount + slabs - 1) / slabs) * _capacity;
        workspace?.EnsureCapacity(entries.Length);
        int[] order = workspace?.Order ?? new int[entries.Length];
        bool exactInteger = SpatialMeasure<TCoordinate>.ExactInteger;
        if (exactInteger) workspace?.EnsureIntegerCapacity(entries.Length, true);
        else workspace?.EnsureZCapacity(entries.Length);
        double[]? xCenters = exactInteger ? null : workspace?.XCenters ?? new double[entries.Length];
        double[]? yCenters = exactInteger ? null : workspace?.YCenters ?? new double[entries.Length];
        double[]? zCenters = exactInteger ? null : workspace?.ZCenters ?? new double[entries.Length];
        BigInteger[]? xIntegerCenters = exactInteger ? workspace?.XIntegerCenters ?? new BigInteger[entries.Length] : null;
        BigInteger[]? yIntegerCenters = exactInteger ? workspace?.YIntegerCenters ?? new BigInteger[entries.Length] : null;
        BigInteger[]? zIntegerCenters = exactInteger ? workspace?.ZIntegerCenters ?? new BigInteger[entries.Length] : null;
        for (int i = 0; i < entries.Length; i++)
        {
            order[i] = i;
            Box<TCoordinate> bounds = entries[i].Bounds;
            if (exactInteger)
            {
                xIntegerCenters![i] = SpatialMeasure<TCoordinate>.IntegerCenter(bounds.MinX, bounds.MaxX);
                yIntegerCenters![i] = SpatialMeasure<TCoordinate>.IntegerCenter(bounds.MinY, bounds.MaxY);
                zIntegerCenters![i] = SpatialMeasure<TCoordinate>.IntegerCenter(bounds.MinZ, bounds.MaxZ);
            }
            else
            {
                xCenters![i] = SpatialMeasure<TCoordinate>.FloatingCenter(bounds.MinX, bounds.MaxX);
                yCenters![i] = SpatialMeasure<TCoordinate>.FloatingCenter(bounds.MinY, bounds.MaxY);
                zCenters![i] = SpatialMeasure<TCoordinate>.FloatingCenter(bounds.MinZ, bounds.MaxZ);
            }
        }
        IComparer<int> xComparer = exactInteger ? new IntegerAxisComparer(xIntegerCenters!) : new AxisComparer(xCenters!);
        IComparer<int> yComparer = exactInteger ? new IntegerAxisComparer(yIntegerCenters!) : new AxisComparer(yCenters!);
        IComparer<int> zComparer = exactInteger ? new IntegerAxisComparer(zIntegerCenters!) : new AxisComparer(zCenters!);
        Array.Sort(order, 0, entries.Length, xComparer);
        int nextNode = 0;
        for (int slabStart = 0; slabStart < entries.Length; slabStart += slabCapacity)
        {
            int slabLength = Math.Min(slabCapacity, entries.Length - slabStart);
            Array.Sort(order, slabStart, slabLength, yComparer);
            int nodesInSlab = (slabLength + _capacity - 1) / _capacity;
            int rows = (int)Math.Ceiling(Math.Sqrt(nodesInSlab));
            int rowCapacity = ((nodesInSlab + rows - 1) / rows) * _capacity;
            for (int rowStart = slabStart; rowStart < slabStart + slabLength; rowStart += rowCapacity)
            {
                int rowLength = Math.Min(rowCapacity, slabStart + slabLength - rowStart);
                Array.Sort(order, rowStart, rowLength, zComparer);
                for (int offset = 0; offset < rowLength; offset += _capacity)
                {
                    Node node = new(leaf, _capacity);
                    int end = Math.Min(offset + _capacity, rowLength);
                    for (int i = offset; i < end; i++)
                        Add(node, entries[order[rowStart + i]]);
                    nodes[nextNode++] = node;
                }
            }
        }
        return nodes;
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
            Node child = node.Entries[selected].Child!;
            Insert(child, entry, out Node? childSibling);
            node.Entries[selected].Bounds = child.Bounds;
            node.Bounds = Box<TCoordinate>.Union(node.Bounds, child.Bounds);
            if (childSibling is not null)
                Add(node, new Entry(childSibling.Bounds, childSibling, default!));
        }

        sibling = node.Count > _capacity ? Split(node) : null;
    }

    private static int ChooseSubtree(Node node, in Box<TCoordinate> bounds)
    {
        int best = 0;
        SpatialMeasure<TCoordinate> bestEnlargement = SpatialMeasure<TCoordinate>.PositiveInfinity;
        SpatialMeasure<TCoordinate> bestArea = SpatialMeasure<TCoordinate>.PositiveInfinity;
        for (int i = 0; i < node.Count; i++)
        {
            Box<TCoordinate> current = node.Entries[i].Bounds;
            SpatialMeasure<TCoordinate> area = current.Area;
            SpatialMeasure<TCoordinate> enlargement = Enlargement(current, bounds);
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
        Array.Copy(node.Entries, entries, length);
        int seedA = 0, seedB = 1;
        SpatialMeasure<TCoordinate> worstWaste = SpatialMeasure<TCoordinate>.NegativeInfinity;
        for (int i = 0; i < length - 1; i++)
        {
            for (int j = i + 1; j < length; j++)
            {
                SpatialMeasure<TCoordinate> waste = Box<TCoordinate>.Union(entries[i].Bounds, entries[j].Bounds).Area -
                    entries[i].Bounds.Area - entries[j].Bounds.Area;
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
            SpatialMeasure<TCoordinate> greatestDifference = SpatialMeasure<TCoordinate>.NegativeInfinity;
            SpatialMeasure<TCoordinate> enlargementA = SpatialMeasure<TCoordinate>.Zero, enlargementB = SpatialMeasure<TCoordinate>.Zero;
            for (int i = 0; i < length; i++)
            {
                if (assigned[i]) continue;
                SpatialMeasure<TCoordinate> a = Enlargement(node.Bounds, entries[i].Bounds);
                SpatialMeasure<TCoordinate> b = Enlargement(other.Bounds, entries[i].Bounds);
                SpatialMeasure<TCoordinate> difference = SpatialMeasure<TCoordinate>.Abs(a - b);
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
                node.Bounds.Area < other.Bounds.Area ? node :
                other.Bounds.Area < node.Bounds.Area ? other :
                node.Count <= other.Count ? node : other;
            Add(destination, entries[selected]);
            assigned[selected] = true;
            remaining--;
        }
        // The vacated slots otherwise retain values and child nodes after a split.
        Array.Clear(node.Entries, node.Count, length - node.Count);
        return other;
    }

    private static SpatialMeasure<TCoordinate> Enlargement(in Box<TCoordinate> current, in Box<TCoordinate> added)
    {
        SpatialMeasure<TCoordinate> before = current.Area;
        SpatialMeasure<TCoordinate> after = Box<TCoordinate>.Union(current, added).Area;
        return after > before ? after - before : SpatialMeasure<TCoordinate>.Zero;
    }

    private static void Add(Node node, Entry entry)
    {
        node.Entries[node.Count++] = entry;
        node.Bounds = node.Count == 1 ? entry.Bounds : Box<TCoordinate>.Union(node.Bounds, entry.Bounds);
    }

}
