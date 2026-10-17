namespace Tedd.RTree;

// Fast 16-bit Hilbert transform, derived from the public-domain algorithm by
// rawrunprotected/hilbert_curves (also used by Flatbush and the Rust packed indexes).
internal static class HilbertOrder
{
    internal static uint Encode(uint x, uint y)
    {
        uint a = x ^ y, b = 0xFFFF ^ a, c = 0xFFFF ^ (x | y), d = x & (y ^ 0xFFFF);
        uint A = a | (b >> 1), B = (a >> 1) ^ a;
        uint C = ((c >> 1) ^ (b & (d >> 1))) ^ c;
        uint D = ((a & (c >> 1)) ^ (d >> 1)) ^ d;
        a = A; b = B; c = C; d = D;
        A = (a & (a >> 2)) ^ (b & (b >> 2));
        B = (a & (b >> 2)) ^ (b & ((a ^ b) >> 2));
        C ^= (a & (c >> 2)) ^ (b & (d >> 2));
        D ^= (b & (c >> 2)) ^ ((a ^ b) & (d >> 2));
        a = A; b = B; c = C; d = D;
        A = (a & (a >> 4)) ^ (b & (b >> 4));
        B = (a & (b >> 4)) ^ (b & ((a ^ b) >> 4));
        C ^= (a & (c >> 4)) ^ (b & (d >> 4));
        D ^= (b & (c >> 4)) ^ ((a ^ b) & (d >> 4));
        a = A; b = B; c = C; d = D;
        C ^= (a & (c >> 8)) ^ (b & (d >> 8));
        D ^= (b & (c >> 8)) ^ ((a ^ b) & (d >> 8));
        a = C ^ (C >> 1); b = D ^ (D >> 1);
        uint i0 = x ^ y, i1 = b | (0xFFFF ^ (i0 | a));
        i0 = Spread(i0); i1 = Spread(i1);
        return (i1 << 1) | i0;
    }

    private static uint Spread(uint x)
    {
        x = (x | (x << 8)) & 0x00FF00FF;
        x = (x | (x << 4)) & 0x0F0F0F0F;
        x = (x | (x << 2)) & 0x33333333;
        return (x | (x << 1)) & 0x55555555;
    }
}
