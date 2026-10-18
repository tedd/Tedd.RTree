using System.Numerics;
using System.Runtime.CompilerServices;

namespace Tedd.RTree;

// Quantization controls packing only. All stored bounds and predicates remain TCoordinate.
internal readonly struct SpatialKeyAxis<TCoordinate> where TCoordinate : struct, INumber<TCoordinate>
{
    private readonly Int128 _integerOrigin;
    private readonly double _minimum, _width, _scale;
    private readonly uint _maximumKey;

    internal SpatialKeyAxis(TCoordinate min, TCoordinate max, uint maximumKey)
    {
        _maximumKey = maximumKey;
        if (SpatialMeasure<TCoordinate>.ExactInteger)
        {
            // Int128 accommodates doubled long endpoints and their full signed-range difference.
            Int128 low = Int128.CreateChecked(min), high = Int128.CreateChecked(max);
            _integerOrigin = low * 2;
            _minimum = 0;
            _width = double.CreateChecked((high - low) * 2);
        }
        else
        {
            _integerOrigin = 0;
            _minimum = double.CreateSaturating(min) * 0.5;
            _width = double.CreateSaturating(max) * 0.5 - _minimum;
        }
        _scale = _width > 0 ? maximumKey / _width : 0;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    internal uint Center(TCoordinate min, TCoordinate max)
    {
        if (!(_width > 0) || !double.IsFinite(_width)) return 0;
        double offset = SpatialMeasure<TCoordinate>.ExactInteger
            ? double.CreateChecked(Int128.CreateChecked(min) + Int128.CreateChecked(max) - _integerOrigin)
            : double.CreateSaturating(min) * 0.25 + double.CreateSaturating(max) * 0.25 - _minimum;
        double key = double.IsFinite(_scale) ? offset * _scale : offset / _width * _maximumKey;
        return double.IsFinite(key) ? (uint)Math.Clamp(key, 0, _maximumKey) : 0;
    }
}
