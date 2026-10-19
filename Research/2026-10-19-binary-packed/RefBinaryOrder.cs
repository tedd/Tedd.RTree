using System.Numerics;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace Tedd.RTree;

internal static class RefBinaryOrder
{
    internal static void Sort(Span<uint> keys, Span<int> order, int capacity)
    {
        if (keys.Length != order.Length) throw new ArgumentException("Key/order lengths differ.");
        if (keys.Length < 2) return;
        if (capacity != 16) { BinaryOrder.Sort(keys, order, capacity); return; }
        Partition16(ref MemoryMarshal.GetReference(keys), ref MemoryMarshal.GetReference(order), 0, keys.Length - 1, 1u << 31);
    }

    // Every recursive range is a nonempty subrange of the original spans. The scans
    // only read i/j-1 while i<j; swaps and common-prefix scans stay in that range.
    // Managed byrefs remain tracked across moving GC; no raw pointers or pinning.
    private static void Partition16(ref uint keys, ref int order, int left, int right, uint bit)
    {
        int empty = 0, split;
        while (true)
        {
            if ((left >> 4) >= (right >> 4) || bit == 0) return;
            int end = right + 1, i = left, j = end;
            while (i < j)
            {
                while (i < j && (Unsafe.Add(ref keys, i) & bit) == 0) i++;
                while (i < j && (Unsafe.Add(ref keys, j - 1) & bit) != 0) j--;
                if (i == j) break;
                ref uint a = ref Unsafe.Add(ref keys, i), b = ref Unsafe.Add(ref keys, j - 1);
                (a, b) = (b, a);
                ref int x = ref Unsafe.Add(ref order, i), y = ref Unsafe.Add(ref order, j - 1);
                (x, y) = (y, x);
                i++; j--;
            }
            bit >>= 1;
            if (i == left || i == end)
            {
                if (++empty == 2)
                {
                    uint first = Unsafe.Add(ref keys, left), different = 0;
                    for (int k = left + 1; k <= right; k++) different |= first ^ Unsafe.Add(ref keys, k);
                    if (different == 0) return;
                    bit = 1u << BitOperations.Log2(different);
                    empty = 0;
                }
                continue;
            }
            split = i;
            break;
        }
        Partition16(ref keys, ref order, left, split - 1, bit);
        Partition16(ref keys, ref order, split, right, bit);
    }
}
