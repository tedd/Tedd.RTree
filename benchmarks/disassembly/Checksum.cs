using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Intrinsics;
using System.Runtime.Intrinsics.X86;

// Benchmark consumer only. Fixture IDs are nonnegative and below 100,000;
// summing IDs and then adding Length equals the original sum of (int ID + 1).
internal static class Checksum
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    internal static long Span(List<int> result)
    {
        long sum = 0;
        foreach (int id in CollectionsMarshal.AsSpan(result)) sum += id + 1;
        return sum;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    internal static long Vector(List<int> result)
    {
        ReadOnlySpan<int> ids = CollectionsMarshal.AsSpan(result);
        int i = 0;
        long sum = 0;
        if (Avx2.IsSupported)
        {
            ref int first = ref MemoryMarshal.GetReference(ids);
            var a = Vector256<long>.Zero;
            var b = Vector256<long>.Zero;
            var c = Vector256<long>.Zero;
            var d = Vector256<long>.Zero;
            for (; i <= ids.Length - 16; i += 16)
            {
                var x = Vector256.LoadUnsafe(ref first, (nuint)i);
                var y = Vector256.LoadUnsafe(ref first, (nuint)(i + 8));
                a += Vector256.WidenLower(x);
                b += Vector256.WidenUpper(x);
                c += Vector256.WidenLower(y);
                d += Vector256.WidenUpper(y);
            }
            if (i <= ids.Length - 8)
            {
                var x = Vector256.LoadUnsafe(ref first, (nuint)i);
                a += Vector256.WidenLower(x);
                b += Vector256.WidenUpper(x);
                i += 8;
            }
            sum = Vector256.Sum((a + b) + (c + d));
        }
        for (; i < ids.Length; i++) sum += ids[i];
        return sum + ids.Length;
    }
}
