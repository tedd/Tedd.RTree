using System.Reflection;
using System.Runtime.Intrinsics;
using Tedd.RTree;

internal static class SpatialKeyVectorChecks
{
    internal static void Run()
    {
        if (!Vector256.IsHardwareAccelerated) return;
        Assembly assembly = typeof(RTree<int>).Assembly;
        const BindingFlags flags = BindingFlags.Static | BindingFlags.NonPublic;
        Type hilbert = assembly.GetType("Tedd.RTree.HilbertOrder", throwOnError: true)!;
        Type morton = assembly.GetType("Tedd.RTree.SpatialOrder3D", throwOnError: true)!;
        var vector2 = hilbert.GetMethod("Encode", flags, [typeof(Vector256<uint>), typeof(Vector256<uint>)]);
        var vector3 = morton.GetMethod("Morton", flags, [typeof(Vector256<uint>), typeof(Vector256<uint>), typeof(Vector256<uint>)]);
        // The retained control has scalar helpers only. Keep the oracle usable
        // against both frozen assemblies without adding a public test hook.
        if (vector2 is null && vector3 is null) return;
        var scalar2 = hilbert.GetMethod("Encode", flags, [typeof(uint), typeof(uint)])!
            .CreateDelegate<Func<uint, uint, uint>>();
        var scalar3 = morton.GetMethod("Morton", flags, [typeof(uint), typeof(uint), typeof(uint)])!
            .CreateDelegate<Func<uint, uint, uint, uint>>();
        var encode2 = vector2?.CreateDelegate<Func<Vector256<uint>, Vector256<uint>, Vector256<uint>>>();
        var encode3 = vector3?.CreateDelegate<Func<Vector256<uint>, Vector256<uint>, Vector256<uint>, Vector256<uint>>>();
        Span<uint> xs = stackalloc uint[8], ys = stackalloc uint[8], zs = stackalloc uint[8];
        Span<uint> actual = stackalloc uint[8];
        uint random = 0x31415926;
        uint Next() => random = unchecked(random * 1664525 + 1013904223);
        for (uint first = 0; first < 65536; first += 8)
        {
            for (int lane = 0; lane < 8; lane++)
            {
                xs[lane] = first + (uint)lane;
                ys[lane] = Next() & 65535;
            }
            if (encode2 is not null)
            {
                encode2(Vector256.Create(xs), Vector256.Create(ys)).CopyTo(actual);
                for (int lane = 0; lane < 8; lane++)
                    if (actual[lane] != scalar2(xs[lane], ys[lane]))
                        throw new Exception("Vector Hilbert key differs from scalar key.");
            }
            for (int lane = 0; lane < 8; lane++)
            {
                xs[lane] &= 1023;
                ys[lane] &= 1023;
                zs[lane] = Next() & 1023;
            }
            if (encode3 is not null)
            {
                encode3(Vector256.Create(xs), Vector256.Create(ys), Vector256.Create(zs)).CopyTo(actual);
                for (int lane = 0; lane < 8; lane++)
                    if (actual[lane] != scalar3(xs[lane], ys[lane], zs[lane]))
                        throw new Exception("Vector Morton key differs from scalar key.");
            }
        }
    }
}
