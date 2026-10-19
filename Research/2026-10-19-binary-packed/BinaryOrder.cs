using System.Numerics;

namespace Tedd.RTree;

// Binary MSD partitioning establishes final leaf membership, not ordering within a leaf.
// The stop condition uses absolute output positions, including non-power-of-two capacities.
internal static class BinaryOrder
{
    internal static void Sort(Span<uint> keys, Span<int> order, int capacity) =>
        Partition(keys, order, 0, keys.Length - 1, capacity, 1u << 31);

    private static void Partition(Span<uint> keys, Span<int> order, int left, int right, int capacity, uint bit)
    {
        int empty = 0, split;
        while (true)
        {
            if (left / capacity >= right / capacity || bit == 0) return;
            int end = right + 1, i = left, j = end;
            while (i < j)
            {
                while (i < j && (keys[i] & bit) == 0) i++;
                while (i < j && (keys[j - 1] & bit) != 0) j--;
                if (i == j) break;
                (keys[i], keys[j - 1]) = (keys[j - 1], keys[i]);
                (order[i], order[j - 1]) = (order[j - 1], order[i]);
                i++; j--;
            }
            bit >>= 1;
            if (i == left || i == end)
            {
                if (++empty == 2)
                {
                    uint first = keys[left], different = 0;
                    for (int k = left + 1; k <= right; k++) different |= first ^ keys[k];
                    if (different == 0) return;
                    bit = 1u << BitOperations.Log2(different);
                    empty = 0;
                }
                continue;
            }
            split = i;
            break;
        }
        Partition(keys, order, left, split - 1, capacity, bit);
        Partition(keys, order, split, right, capacity, bit);
    }

    internal static void SortOwned<T>(Span<uint> keys, Rectangle[] boxes, T[] values, int count, int capacity) =>
        PartitionOwned(keys, boxes, values, 0, count - 1, capacity, 1u << 31);

    private static void PartitionOwned<T>(Span<uint> keys, Rectangle[] boxes, T[] values, int left, int right, int capacity, uint bit)
    {
        int empty = 0, split;
        while (true)
        {
            if (left / capacity >= right / capacity || bit == 0) return;
            int end = right + 1, i = left, j = end;
            while (i < j)
            {
                while (i < j && (keys[i] & bit) == 0) i++;
                while (i < j && (keys[j - 1] & bit) != 0) j--;
                if (i == j) break;
                (keys[i], keys[j - 1]) = (keys[j - 1], keys[i]);
                (boxes[i], boxes[j - 1]) = (boxes[j - 1], boxes[i]);
                (values[i], values[j - 1]) = (values[j - 1], values[i]);
                i++; j--;
            }
            bit >>= 1;
            if (i == left || i == end)
            {
                if (++empty == 2)
                {
                    uint first = keys[left], different = 0;
                    for (int k = left + 1; k <= right; k++) different |= first ^ keys[k];
                    if (different == 0) return;
                    bit = 1u << BitOperations.Log2(different);
                    empty = 0;
                }
                continue;
            }
            split = i;
            break;
        }
        PartitionOwned(keys, boxes, values, left, split - 1, capacity, bit);
        PartitionOwned(keys, boxes, values, split, right, capacity, bit);
    }
}
