using System.Numerics;

namespace Tedd.RTree;

// Node-selection metrics are exact for int/long coordinates. Search predicates always use
// the original coordinate type; this metric affects tree shape, never match correctness.
internal readonly struct SpatialMeasure<TCoordinate> : IComparable<SpatialMeasure<TCoordinate>>
    where TCoordinate : struct, INumber<TCoordinate>
{
    internal static readonly bool ExactInteger = typeof(TCoordinate) == typeof(int) || typeof(TCoordinate) == typeof(long);

    private readonly BigInteger _integer;
    private readonly double _floating;
    private readonly sbyte _infinity;

    private SpatialMeasure(BigInteger value) => (_integer, _floating, _infinity) = (value, 0, 0);
    private SpatialMeasure(double value) => (_integer, _floating, _infinity) = (default, value, 0);
    private SpatialMeasure(sbyte infinity) => (_integer, _floating, _infinity) = (default, 0, infinity);

    internal static SpatialMeasure<TCoordinate> Zero => ExactInteger ? new(BigInteger.Zero) : new(0.0);
    internal static SpatialMeasure<TCoordinate> PositiveInfinity => new((sbyte)1);
    internal static SpatialMeasure<TCoordinate> NegativeInfinity => new((sbyte)-1);

    internal static SpatialMeasure<TCoordinate> Area(
        TCoordinate minX, TCoordinate maxX, TCoordinate minY, TCoordinate maxY)
    {
        if (ExactInteger)
            return new((BigInteger.CreateChecked(maxX) - BigInteger.CreateChecked(minX)) *
                (BigInteger.CreateChecked(maxY) - BigInteger.CreateChecked(minY)));
        double area = (double.CreateSaturating(maxX) - double.CreateSaturating(minX)) *
            (double.CreateSaturating(maxY) - double.CreateSaturating(minY));
        return new(double.IsFinite(area) ? area : double.MaxValue);
    }

    internal static SpatialMeasure<TCoordinate> Volume(
        TCoordinate minX, TCoordinate maxX, TCoordinate minY, TCoordinate maxY,
        TCoordinate minZ, TCoordinate maxZ)
    {
        if (ExactInteger)
            return new((BigInteger.CreateChecked(maxX) - BigInteger.CreateChecked(minX)) *
                (BigInteger.CreateChecked(maxY) - BigInteger.CreateChecked(minY)) *
                (BigInteger.CreateChecked(maxZ) - BigInteger.CreateChecked(minZ)));
        double volume = (double.CreateSaturating(maxX) - double.CreateSaturating(minX)) *
            (double.CreateSaturating(maxY) - double.CreateSaturating(minY)) *
            (double.CreateSaturating(maxZ) - double.CreateSaturating(minZ));
        return new(double.IsFinite(volume) ? volume : double.MaxValue);
    }

    internal static BigInteger IntegerCenter(TCoordinate min, TCoordinate max) =>
        BigInteger.CreateChecked(min) + BigInteger.CreateChecked(max);

    internal static double FloatingCenter(TCoordinate min, TCoordinate max) =>
        double.CreateSaturating(min) * 0.5 + double.CreateSaturating(max) * 0.5;

    public int CompareTo(SpatialMeasure<TCoordinate> other)
    {
        if (_infinity != 0 || other._infinity != 0)
            return _infinity.CompareTo(other._infinity);
        return ExactInteger ? _integer.CompareTo(other._integer) : _floating.CompareTo(other._floating);
    }

    internal static SpatialMeasure<TCoordinate> Abs(SpatialMeasure<TCoordinate> value) =>
        ExactInteger ? new(BigInteger.Abs(value._integer)) : new(Math.Abs(value._floating));

    public static SpatialMeasure<TCoordinate> operator -(SpatialMeasure<TCoordinate> left, SpatialMeasure<TCoordinate> right) =>
        ExactInteger ? new(left._integer - right._integer) : new(left._floating - right._floating);
    public static bool operator <(SpatialMeasure<TCoordinate> left, SpatialMeasure<TCoordinate> right) => left.CompareTo(right) < 0;
    public static bool operator >(SpatialMeasure<TCoordinate> left, SpatialMeasure<TCoordinate> right) => left.CompareTo(right) > 0;
    public static bool operator ==(SpatialMeasure<TCoordinate> left, SpatialMeasure<TCoordinate> right) => left.CompareTo(right) == 0;
    public static bool operator !=(SpatialMeasure<TCoordinate> left, SpatialMeasure<TCoordinate> right) => left.CompareTo(right) != 0;
    public override bool Equals(object? obj) => obj is SpatialMeasure<TCoordinate> other && this == other;
    public override int GetHashCode() => ExactInteger ? _integer.GetHashCode() : _floating.GetHashCode();
}
