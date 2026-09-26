namespace Tedd.RTree;

/// <summary>An immutable, axis-aligned two-dimensional rectangle. Edges are inclusive.</summary>
public readonly struct Rectangle : IEquatable<Rectangle>
{
    /// <summary>Minimum horizontal coordinate.</summary>
    public double MinX { get; }
    /// <summary>Minimum vertical coordinate.</summary>
    public double MinY { get; }
    /// <summary>Maximum horizontal coordinate.</summary>
    public double MaxX { get; }
    /// <summary>Maximum vertical coordinate.</summary>
    public double MaxY { get; }

    /// <summary>Creates a rectangle from finite, ordered coordinates.</summary>
    public Rectangle(double minX, double minY, double maxX, double maxY)
    {
        if (!double.IsFinite(minX) || !double.IsFinite(minY) ||
            !double.IsFinite(maxX) || !double.IsFinite(maxY) ||
            minX > maxX || minY > maxY)
            throw new ArgumentOutOfRangeException(nameof(minX), "Coordinates must be finite and ordered.");

        MinX = minX;
        MinY = minY;
        MaxX = maxX;
        MaxY = maxY;
    }

    private Rectangle(in Rectangle a, in Rectangle b)
    {
        // Both operands already have finite, ordered coordinates. Min/Max preserve that invariant.
        MinX = Math.Min(a.MinX, b.MinX);
        MinY = Math.Min(a.MinY, b.MinY);
        MaxX = Math.Max(a.MaxX, b.MaxX);
        MaxY = Math.Max(a.MaxY, b.MaxY);
    }

    /// <summary>Whether this rectangle intersects or touches another.</summary>
    public bool Intersects(in Rectangle other) =>
        MinX <= other.MaxX && MaxX >= other.MinX &&
        MinY <= other.MaxY && MaxY >= other.MinY;

    /// <summary>Whether this rectangle contains another, including its boundary.</summary>
    public bool Contains(in Rectangle other) =>
        MinX <= other.MinX && MinY <= other.MinY &&
        MaxX >= other.MaxX && MaxY >= other.MaxY;

    internal double Area
    {
        get
        {
            double area = (MaxX - MinX) * (MaxY - MinY);
            return double.IsFinite(area) ? area : double.MaxValue;
        }
    }

    internal static Rectangle Union(in Rectangle a, in Rectangle b) => new(a, b);

    /// <inheritdoc />
    public bool Equals(Rectangle other) => MinX == other.MinX && MinY == other.MinY &&
        MaxX == other.MaxX && MaxY == other.MaxY;

    /// <inheritdoc />
    public override bool Equals(object? obj) => obj is Rectangle other && Equals(other);
    /// <inheritdoc />
    public override int GetHashCode() => HashCode.Combine(MinX, MinY, MaxX, MaxY);
    /// <summary>Compares rectangle coordinates.</summary>
    public static bool operator ==(Rectangle left, Rectangle right) => left.Equals(right);
    /// <summary>Compares rectangle coordinates.</summary>
    public static bool operator !=(Rectangle left, Rectangle right) => !left.Equals(right);
}
