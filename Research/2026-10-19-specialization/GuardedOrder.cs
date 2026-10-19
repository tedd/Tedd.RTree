namespace Tedd.RTree;

internal static class GuardedOrder
{
    internal static void Sort(ReadOnlySpan<uint> keys, Span<int> order, Span<int> scratch, int capacity)
        => Partition(keys, order, scratch, 0, order.Length, 24, capacity);

    private static void Partition(ReadOnlySpan<uint> keys, Span<int> order, Span<int> scratch,
        int start, int end, int shift, int capacity)
    {
        if (end - start <= 1 || shift < 0 || start / capacity == (end - 1) / capacity) return;
        Span<int> ends = stackalloc int[256];
        ends.Clear();
        for (int i = start; i < end; i++) ends[(int)(keys[order[i]] >> shift) & 255]++;
        int sum = start;
        for (int i = 0; i < ends.Length; i++) { int count = ends[i]; ends[i] = sum; sum += count; }
        for (int i = start; i < end; i++)
        {
            int index = order[i];
            scratch[ends[(int)(keys[index] >> shift) & 255]++] = index;
        }
        scratch.Slice(start, end - start).CopyTo(order.Slice(start, end - start));
        int previous = start;
        for (int i = 0; i < ends.Length; i++)
        {
            int next = ends[i];
            if (shift > 0 && next - previous > 1 && previous / capacity != (next - 1) / capacity)
                Partition(keys, order, scratch, previous, next, shift - 8, capacity);
            previous = next;
        }
    }
}
