using System.Numerics;

namespace Tedd.RTree;

/// <summary>An item and its axis-aligned spatial bounds.</summary>
public readonly record struct SpatialEntry2D<TCoordinate, TItem>(Rectangle2D<TCoordinate> Bounds, TItem Item)
    where TCoordinate : struct, INumber<TCoordinate>;
