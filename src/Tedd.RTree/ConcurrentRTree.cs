using System.Threading;

namespace Tedd.RTree;

/// <summary>A thread-safe mutable R-tree with immediately visible individual moves.</summary>
/// <remarks>
/// Values serve as stable, unique keys. Their equality and hash codes must not change while indexed.
/// Searches hold a read lock; additions, moves, removals, and bulk loading hold a write lock.
/// </remarks>
public sealed class ConcurrentRTree<T> : IDisposable where T : notnull
{
    private readonly ReaderWriterLockSlim _lock = new();
    private readonly int _maxEntries;
    private RTree<T> _tree;
    private Dictionary<T, Rectangle> _locations = [];

    /// <param name="maxEntries">Maximum entries per node, from 4 to 128.</param>
    public ConcurrentRTree(int maxEntries = 16)
    {
        _tree = new RTree<T>(maxEntries);
        _maxEntries = maxEntries;
    }

    /// <summary>Number of indexed entries.</summary>
    public int Count
    {
        get
        {
            _lock.EnterReadLock();
            try { return _locations.Count; }
            finally { _lock.ExitReadLock(); }
        }
    }

    /// <summary>Loads an initial batch. The index must be empty and values must be unique.</summary>
    /// <remarks>The caller must not change the input batch while this method runs.</remarks>
    public void BulkLoad(IReadOnlyList<SpatialEntry<T>> items)
    {
        ArgumentNullException.ThrowIfNull(items);
        _lock.EnterWriteLock();
        try
        {
            if (_locations.Count != 0)
                throw new InvalidOperationException("Bulk loading requires an empty index.");
            Dictionary<T, Rectangle> locations = new(items.Count);
            for (int i = 0; i < items.Count; i++)
                if (!locations.TryAdd(items[i].Item, items[i].Bounds))
                    throw new ArgumentException("Bulk loading requires unique values.", nameof(items));
            RTree<T> next = new(_maxEntries);
            next.BulkLoad(items);
            _tree = next;
            _locations = locations;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Adds a value at the given bounds.</summary>
    /// <returns>False if the value is already indexed.</returns>
    public bool Add(Rectangle bounds, T item)
    {
        ArgumentNullException.ThrowIfNull(item);
        _lock.EnterWriteLock();
        try
        {
            if (_locations.ContainsKey(item)) return false;
            _tree.Insert(bounds, item);
            _locations.Add(item, bounds);
            return true;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Moves one indexed value. Successful moves are visible to subsequent searches.</summary>
    /// <returns>False if the value is not indexed.</returns>
    public bool Move(T item, Rectangle newBounds)
    {
        ArgumentNullException.ThrowIfNull(item);
        _lock.EnterWriteLock();
        try
        {
            if (!_locations.TryGetValue(item, out Rectangle oldBounds)) return false;
            if (oldBounds == newBounds) return true;
            if (!_tree.Update(oldBounds, item, newBounds))
                throw new InvalidOperationException("The location map and tree disagree.");
            _locations[item] = newBounds;
            return true;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Removes an indexed value.</summary>
    /// <returns>False if the value is not indexed.</returns>
    public bool Remove(T item)
    {
        ArgumentNullException.ThrowIfNull(item);
        _lock.EnterWriteLock();
        try
        {
            if (!_locations.TryGetValue(item, out Rectangle bounds)) return false;
            if (!_tree.Remove(bounds, item))
                throw new InvalidOperationException("The location map and tree disagree.");
            _locations.Remove(item);
            return true;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Appends intersecting values to <paramref name="results"/> and returns the number appended.</summary>
    /// <remarks>Each concurrent search must use a separate result list.</remarks>
    public int Search(Rectangle bounds, List<T> results)
    {
        _lock.EnterReadLock();
        try { return _tree.Search(bounds, results); }
        finally { _lock.ExitReadLock(); }
    }

    /// <summary>Appends matches for each query to its result list and writes the appended counts.</summary>
    /// <returns>The total number of matches appended across all queries.</returns>
    /// <remarks>
    /// Results must have one non-null list per query; counts must have at least one slot per query.
    /// Existing list contents are preserved. Inputs and output storage must not be changed concurrently.
    /// The whole batch holds one read lock, so writers wait until the batch completes.
    /// </remarks>
    public long SearchBatch(ReadOnlySpan<Rectangle> queries, ReadOnlySpan<List<T>> results, Span<int> counts)
    {
        _lock.EnterReadLock();
        try { return _tree.SearchBatch(queries, results, counts); }
        finally { _lock.ExitReadLock(); }
    }

    /// <summary>Returns intersecting values in a new list.</summary>
    public List<T> Search(Rectangle bounds)
    {
        _lock.EnterReadLock();
        try { return _tree.Search(bounds); }
        finally { _lock.ExitReadLock(); }
    }

    /// <summary>Removes all indexed values.</summary>
    public void Clear()
    {
        _lock.EnterWriteLock();
        try
        {
            _tree.Clear();
            _locations.Clear();
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Releases the synchronization object after callers have stopped using this index.</summary>
    public void Dispose() => _lock.Dispose();
}
