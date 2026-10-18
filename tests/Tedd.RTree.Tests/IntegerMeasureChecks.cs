using System.Numerics;
using System.Reflection;
using Tedd.RTree;

internal static class IntegerMeasureChecks
{
    internal static void Run()
    {
        Check<int>(new[] { int.MinValue, -2097152, -2097151, -1, 0, 1, 2097151, 2097152, int.MaxValue });
        Check<long>(new[] { long.MinValue, -4294967296, -4294967295, -2097152, -2097151, -1, 0, 1,
            2097151, 2097152, 4294967295, 4294967296, 9007199254740992, 9007199254740993, long.MaxValue });
    }

    private static void Check<C>(C[] values) where C : struct, INumber<C>
    {
        var type = typeof(RTree<int>).Assembly.GetType("Tedd.RTree.SpatialMeasure`1")!.MakeGenericType(typeof(C));
        var area = type.GetMethod("Area", BindingFlags.Static | BindingFlags.NonPublic)!;
        var volume = type.GetMethod("Volume", BindingFlags.Static | BindingFlags.NonPublic)!;
        var integer = type.GetField("_integer", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var extents = (from lo in values from hi in values where lo <= hi select (lo, hi)).ToArray();
        // Independently calculate expected products at fixed-width boundaries and full signed ranges.
        for (int i = 0; i < extents.Length; i++)
        for (int j = 0; j < extents.Length; j++)
        {
            var x = extents[i]; var y = extents[j]; var z = extents[(i * 17 + j * 31) % extents.Length];
            BigInteger dx = BigInteger.CreateChecked(x.hi) - BigInteger.CreateChecked(x.lo);
            BigInteger dy = BigInteger.CreateChecked(y.hi) - BigInteger.CreateChecked(y.lo);
            BigInteger dz = BigInteger.CreateChecked(z.hi) - BigInteger.CreateChecked(z.lo);
            var actualArea = (BigInteger)integer.GetValue(area.Invoke(null, [x.lo, x.hi, y.lo, y.hi]))!;
            var actualVolume = (BigInteger)integer.GetValue(volume.Invoke(null, [x.lo, x.hi, y.lo, y.hi, z.lo, z.hi]))!;
            if (actualArea != dx * dy || actualVolume != dx * dy * dz) throw new Exception("Exact bounded integer metric oracle");
        }
    }
}
