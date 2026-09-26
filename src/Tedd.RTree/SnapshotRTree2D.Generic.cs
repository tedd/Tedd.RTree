using System.Threading;

namespace Tedd.RTree;

/// <summary>A thread-safe R-tree for replacing a complete batch of moving entries.</summary>
/// <remarks>
/// Searches use one complete published tree and do not wait for a replacement build.
/// The previous tree may remain alive while a search is using it. Concurrent replacements
/// are serialized; the last completed replacement becomes current.
/// </remarks>
public sealed class SnapshotRTree2D<TCoordinate, T>
    where TCoordinate : struct, System.Numerics.INumber<TCoordinate>
{
    private readonly int _maxEntries;
    private readonly Lock _writer = new();
    private readonly BulkLoadWorkspace _workspace = new();
    private RTree2D<TCoordinate, T> _current;

    /// <param name="maxEntries">Maximum entries per node, from 4 to 128.</param>
    public SnapshotRTree2D(int maxEntries = 16)
    {
        _current = new RTree2D<TCoordinate, T>(maxEntries);
        _maxEntries = maxEntries;
    }

    /// <summary>Number of entries in the current published tree.</summary>
    public int Count => Volatile.Read(ref _current).Count;

    /// <summary>
    /// Builds and publishes a complete replacement. The input must not be changed while this method runs.
    /// Searches already in progress continue on the previous version.
    /// </summary>
    public void ReplaceAll(IReadOnlyList<SpatialEntry2D<TCoordinate, T>> items)
    {
        ArgumentNullException.ThrowIfNull(items);
        lock (_writer)
        {
            RTree2D<TCoordinate, T> next = new(_maxEntries);
            next.BulkLoad(items, _workspace);
            Volatile.Write(ref _current, next);
        }
    }

    /// <summary>Appends intersecting items from one published version to <paramref name="results"/>.</summary>
    /// <remarks>Each concurrent search must use a separate result list.</remarks>
    public int Search(Rectangle2D<TCoordinate> bounds, List<T> results)
        => Volatile.Read(ref _current).Search(bounds, results);

    /// <summary>Returns intersecting items from one published version in a new list.</summary>
    public List<T> Search(Rectangle2D<TCoordinate> bounds)
        => Volatile.Read(ref _current).Search(bounds);
}
