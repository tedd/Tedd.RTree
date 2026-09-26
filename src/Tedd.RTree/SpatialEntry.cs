namespace Tedd.RTree;

/// <summary>An item and its axis-aligned spatial bounds.</summary>
public readonly record struct SpatialEntry<T>(Rectangle Bounds, T Item);
