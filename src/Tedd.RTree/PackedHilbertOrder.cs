using System.Runtime.Intrinsics;

namespace Tedd.RTree;

// Eight-lane form of the public-domain Hilbert transform used by HilbertOrder.
internal static class PackedHilbertOrder
{
    internal static Vector256<uint> Encode(Vector256<uint> x, Vector256<uint> y)
    {
        Vector256<uint> a = x ^ y, b = Vector256.Create(0xFFFFu) ^ a, c = Vector256.Create(0xFFFFu) ^ (x | y), d = x & (y ^ Vector256.Create(0xFFFFu));
        Vector256<uint> A = a | (b >> 1), B = (a >> 1) ^ a;
        Vector256<uint> C = ((c >> 1) ^ (b & (d >> 1))) ^ c;
        Vector256<uint> D = ((a & (c >> 1)) ^ (d >> 1)) ^ d;
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
        Vector256<uint> i0 = x ^ y, i1 = b | (Vector256.Create(0xFFFFu) ^ (i0 | a));
        i0 = Spread(i0); i1 = Spread(i1);
        return (i1 << 1) | i0;
    }

    private static Vector256<uint> Spread(Vector256<uint> x)
    {
        x = (x | (x << 8)) & Vector256.Create(0x00FF00FFu);
        x = (x | (x << 4)) & Vector256.Create(0x0F0F0F0Fu);
        x = (x | (x << 2)) & Vector256.Create(0x33333333u);
        return (x | (x << 1)) & Vector256.Create(0x55555555u);
    }
}
