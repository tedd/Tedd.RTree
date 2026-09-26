using System.Numerics;

namespace Tedd.RTree;

/// <summary>An immutable, axis-aligned three-dimensional box with inclusive faces.</summary>
public readonly struct Box<TCoordinate> : IEquatable<Box<TCoordinate>>
    where TCoordinate : struct, INumber<TCoordinate>
{
    /// <summary>Minimum X coordinate.</summary>
    public TCoordinate MinX { get; }
    /// <summary>Minimum Y coordinate.</summary>
    public TCoordinate MinY { get; }
    /// <summary>Minimum Z coordinate.</summary>
    public TCoordinate MinZ { get; }
    /// <summary>Maximum X coordinate.</summary>
    public TCoordinate MaxX { get; }
    /// <summary>Maximum Y coordinate.</summary>
    public TCoordinate MaxY { get; }
    /// <summary>Maximum Z coordinate.</summary>
    public TCoordinate MaxZ { get; }

    /// <summary>Creates a box from finite, ordered coordinates.</summary>
    public Box(TCoordinate minX, TCoordinate minY, TCoordinate minZ,
        TCoordinate maxX, TCoordinate maxY, TCoordinate maxZ)
    {
        if (!TCoordinate.IsFinite(minX) || !TCoordinate.IsFinite(minY) || !TCoordinate.IsFinite(minZ) ||
            !TCoordinate.IsFinite(maxX) || !TCoordinate.IsFinite(maxY) || !TCoordinate.IsFinite(maxZ) ||
            minX > maxX || minY > maxY || minZ > maxZ)
            throw new ArgumentOutOfRangeException(nameof(minX), "Coordinates must be finite and ordered.");

        MinX = minX;
        MinY = minY;
        MinZ = minZ;
        MaxX = maxX;
        MaxY = maxY;
        MaxZ = maxZ;
    }

    private Box(in Box<TCoordinate> a, in Box<TCoordinate> b)
    {
        MinX = TCoordinate.Min(a.MinX, b.MinX);
        MinY = TCoordinate.Min(a.MinY, b.MinY);
        MinZ = TCoordinate.Min(a.MinZ, b.MinZ);
        MaxX = TCoordinate.Max(a.MaxX, b.MaxX);
        MaxY = TCoordinate.Max(a.MaxY, b.MaxY);
        MaxZ = TCoordinate.Max(a.MaxZ, b.MaxZ);
    }

    /// <summary>Whether this box intersects or touches another.</summary>
    public bool Intersects(in Box<TCoordinate> other) =>
        MinX <= other.MaxX && MaxX >= other.MinX &&
        MinY <= other.MaxY && MaxY >= other.MinY &&
        MinZ <= other.MaxZ && MaxZ >= other.MinZ;

    /// <summary>Whether this box contains another, including its boundary.</summary>
    public bool Contains(in Box<TCoordinate> other) =>
        MinX <= other.MinX && MinY <= other.MinY && MinZ <= other.MinZ &&
        MaxX >= other.MaxX && MaxY >= other.MaxY && MaxZ >= other.MaxZ;

    // The R-tree uses this volume only to choose and split nodes. Search compares TCoordinate exactly.
    internal SpatialMeasure<TCoordinate> Area =>
        SpatialMeasure<TCoordinate>.Volume(MinX, MaxX, MinY, MaxY, MinZ, MaxZ);

    internal static Box<TCoordinate> Union(in Box<TCoordinate> a, in Box<TCoordinate> b) => new(a, b);

    /// <inheritdoc />
    public bool Equals(Box<TCoordinate> other) => MinX == other.MinX && MinY == other.MinY && MinZ == other.MinZ &&
        MaxX == other.MaxX && MaxY == other.MaxY && MaxZ == other.MaxZ;

    /// <inheritdoc />
    public override bool Equals(object? obj) => obj is Box<TCoordinate> other && Equals(other);
    /// <inheritdoc />
    public override int GetHashCode() => HashCode.Combine(MinX, MinY, MinZ, MaxX, MaxY, MaxZ);
    /// <summary>Compares box coordinates.</summary>
    public static bool operator ==(Box<TCoordinate> left, Box<TCoordinate> right) => left.Equals(right);
    /// <summary>Compares box coordinates.</summary>
    public static bool operator !=(Box<TCoordinate> left, Box<TCoordinate> right) => !left.Equals(right);
}
