namespace Tedd.RTree;

/// <summary>Read operations shared by mutable, immutable and synchronized spatial indexes.</summary>
/// <remarks>Read-only access does not imply that the underlying index is immutable or safe for concurrent mutation.</remarks>
public interface IReadOnlySpatialIndex<TBounds, T> where TBounds : struct
{
    /// <summary>Number of indexed items.</summary>
    int Count { get; }

    /// <summary>Appends intersecting items and returns the number appended.</summary>
    int Search(TBounds bounds, List<T> results);

    /// <summary>Returns a new list containing intersecting items.</summary>
    List<T> Search(TBounds bounds);

    /// <summary>Appends each query's matches to its result list and writes the appended counts.</summary>
    long SearchBatch(ReadOnlySpan<TBounds> queries, ReadOnlySpan<List<T>> results, Span<int> counts);
}

/// <summary>A spatial index supporting individual changes in addition to the shared read operations.</summary>
public interface IMutableSpatialIndex<TBounds, T> : IReadOnlySpatialIndex<TBounds, T> where TBounds : struct
{
    /// <summary>Inserts an item; duplicate values and bounds are permitted.</summary>
    void Insert(TBounds bounds, T item);

    /// <summary>Removes one entry matching both bounds and value.</summary>
    bool Remove(TBounds bounds, T item);

    /// <summary>Moves one matching entry to new bounds.</summary>
    bool Update(TBounds oldBounds, T item, TBounds newBounds);

    /// <summary>Removes all indexed items.</summary>
    void Clear();
}
