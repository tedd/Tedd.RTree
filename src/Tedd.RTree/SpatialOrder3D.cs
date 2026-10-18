namespace Tedd.RTree;

internal static class SpatialOrder3D
{
    // Interleave all three 10-bit axes into a 30-bit spatial key.
    internal static uint Morton(uint x, uint y, uint z) => Spread(x) << 2 | Spread(y) << 1 | Spread(z);

    private static uint Spread(uint x)
    {
        x = (x | x << 16) & 0x030000FF;
        x = (x | x << 8) & 0x0300F00F;
        x = (x | x << 4) & 0x030C30C3;
        return (x | x << 2) & 0x09249249;
    }
}
