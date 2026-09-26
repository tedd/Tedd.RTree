using System.Threading;

namespace Tedd.RTree;

/// <summary>A thread-safe mutable R-tree with immediately visible individual moves.</summary>
/// <remarks>
/// Values serve as stable, unique keys. Their equality and hash codes must not change while indexed.
/// Searches hold a read lock; additions, moves, removals, and bulk loading hold a write lock.
/// </remarks>
public sealed class ConcurrentRTree2D<TCoordinate, T> : IDisposable
    where TCoordinate : struct, System.Numerics.INumber<TCoordinate>
    where T : notnull
{
    private readonly ReaderWriterLockSlim _lock = new();
    private readonly int _maxEntries;
    private RTree2D<TCoordinate, T> _tree;
    private Dictionary<T, Rectangle2D<TCoordinate>> _locations = [];

    /// <param name="maxEntries">Maximum entries per node, from 4 to 128.</param>
    public ConcurrentRTree2D(int maxEntries = 16)
    {
        _tree = new RTree2D<TCoordinate, T>(maxEntries);
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
    public void BulkLoad(IReadOnlyList<SpatialEntry2D<TCoordinate, T>> items)
    {
        ArgumentNullException.ThrowIfNull(items);
        _lock.EnterWriteLock();
        try
        {
            if (_locations.Count != 0)
                throw new InvalidOperationException("Bulk loading requires an empty index.");
            Dictionary<T, Rectangle2D<TCoordinate>> locations = new(items.Count);
            for (int i = 0; i < items.Count; i++)
                if (!locations.TryAdd(items[i].Item, items[i].Bounds))
                    throw new ArgumentException("Bulk loading requires unique values.", nameof(items));
            RTree2D<TCoordinate, T> next = new(_maxEntries);
            next.BulkLoad(items);
            _tree = next;
            _locations = locations;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Adds a value at the given bounds.</summary>
    /// <returns>False if the value is already indexed.</returns>
    public bool Add(Rectangle2D<TCoordinate> bounds, T item)
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
    public bool Move(T item, Rectangle2D<TCoordinate> newBounds)
    {
        ArgumentNullException.ThrowIfNull(item);
        _lock.EnterWriteLock();
        try
        {
            if (!_locations.TryGetValue(item, out Rectangle2D<TCoordinate> oldBounds)) return false;
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
            if (!_locations.TryGetValue(item, out Rectangle2D<TCoordinate> bounds)) return false;
            if (!_tree.Remove(bounds, item))
                throw new InvalidOperationException("The location map and tree disagree.");
            _locations.Remove(item);
            return true;
        }
        finally { _lock.ExitWriteLock(); }
    }

    /// <summary>Appends intersecting values to <paramref name="results"/> and returns the number appended.</summary>
    /// <remarks>Each concurrent search must use a separate result list.</remarks>
    public int Search(Rectangle2D<TCoordinate> bounds, List<T> results)
    {
        _lock.EnterReadLock();
        try { return _tree.Search(bounds, results); }
        finally { _lock.ExitReadLock(); }
    }

    /// <summary>Returns intersecting values in a new list.</summary>
    public List<T> Search(Rectangle2D<TCoordinate> bounds)
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
