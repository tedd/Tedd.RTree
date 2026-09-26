using System.Numerics;

namespace Tedd.RTree;

/// <summary>An item and its three-dimensional spatial bounds.</summary>
public readonly record struct SpatialEntry3D<TCoordinate, TItem>(Box<TCoordinate> Bounds, TItem Item)
    where TCoordinate : struct, INumber<TCoordinate>;
