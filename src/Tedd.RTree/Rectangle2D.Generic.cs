using System.Numerics;

namespace Tedd.RTree;

/// <summary>An immutable, axis-aligned two-dimensional rectangle with inclusive edges.</summary>
/// <typeparam name="TCoordinate">The coordinate type.</typeparam>
public readonly struct Rectangle2D<TCoordinate> : IEquatable<Rectangle2D<TCoordinate>>
    where TCoordinate : struct, INumber<TCoordinate>
{
    /// <summary>Minimum horizontal coordinate.</summary>
    public TCoordinate MinX { get; }
    /// <summary>Minimum vertical coordinate.</summary>
    public TCoordinate MinY { get; }
    /// <summary>Maximum horizontal coordinate.</summary>
    public TCoordinate MaxX { get; }
    /// <summary>Maximum vertical coordinate.</summary>
    public TCoordinate MaxY { get; }

    /// <summary>Creates a rectangle from finite, ordered coordinates.</summary>
    public Rectangle2D(TCoordinate minX, TCoordinate minY, TCoordinate maxX, TCoordinate maxY)
    {
        if (!TCoordinate.IsFinite(minX) || !TCoordinate.IsFinite(minY) ||
            !TCoordinate.IsFinite(maxX) || !TCoordinate.IsFinite(maxY) ||
            minX > maxX || minY > maxY)
            throw new ArgumentOutOfRangeException(nameof(minX), "Coordinates must be finite and ordered.");

        MinX = minX;
        MinY = minY;
        MaxX = maxX;
        MaxY = maxY;
    }

    private Rectangle2D(in Rectangle2D<TCoordinate> a, in Rectangle2D<TCoordinate> b)
    {
        MinX = TCoordinate.Min(a.MinX, b.MinX);
        MinY = TCoordinate.Min(a.MinY, b.MinY);
        MaxX = TCoordinate.Max(a.MaxX, b.MaxX);
        MaxY = TCoordinate.Max(a.MaxY, b.MaxY);
    }

    /// <summary>Whether this rectangle intersects or touches another.</summary>
    public bool Intersects(in Rectangle2D<TCoordinate> other) =>
        MinX <= other.MaxX && MaxX >= other.MinX &&
        MinY <= other.MaxY && MaxY >= other.MinY;

    /// <summary>Whether this rectangle contains another, including its boundary.</summary>
    public bool Contains(in Rectangle2D<TCoordinate> other) =>
        MinX <= other.MinX && MinY <= other.MinY &&
        MaxX >= other.MaxX && MaxY >= other.MaxY;

    internal SpatialMeasure<TCoordinate> Area =>
        SpatialMeasure<TCoordinate>.Area(MinX, MaxX, MinY, MaxY);

    internal static Rectangle2D<TCoordinate> Union(in Rectangle2D<TCoordinate> a, in Rectangle2D<TCoordinate> b) => new(a, b);

    /// <inheritdoc />
    public bool Equals(Rectangle2D<TCoordinate> other) => MinX == other.MinX && MinY == other.MinY &&
        MaxX == other.MaxX && MaxY == other.MaxY;

    /// <inheritdoc />
    public override bool Equals(object? obj) => obj is Rectangle2D<TCoordinate> other && Equals(other);
    /// <inheritdoc />
    public override int GetHashCode() => HashCode.Combine(MinX, MinY, MaxX, MaxY);
    /// <summary>Compares rectangle coordinates.</summary>
    public static bool operator ==(Rectangle2D<TCoordinate> left, Rectangle2D<TCoordinate> right) => left.Equals(right);
    /// <summary>Compares rectangle coordinates.</summary>
    public static bool operator !=(Rectangle2D<TCoordinate> left, Rectangle2D<TCoordinate> right) => !left.Equals(right);
}
