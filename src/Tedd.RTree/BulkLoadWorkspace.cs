namespace Tedd.RTree;

/// <summary>Reusable scratch arrays for bulk loading one tree at a time.</summary>
/// <remarks>Do not use the same workspace concurrently. Its capacity remains allocated until the workspace is collected.</remarks>
public sealed class BulkLoadWorkspace
{
    internal int[] Order;
    private uint[] _keys;
    private int[] _scatter;

    /// <param name="capacity">Initial number of entries the workspace can accommodate.</param>
    public BulkLoadWorkspace(int capacity = 0)
    {
        if (capacity < 0) throw new ArgumentOutOfRangeException(nameof(capacity));
        Order = new int[capacity];
        _keys = new uint[capacity];
        _scatter = new int[capacity];
    }

    /// <summary>Number of entries that fit without growing scratch arrays.</summary>
    public int Capacity => Order.Length;

    internal void EnsureCapacity(int count)
    {
        if (Order.Length >= count) return;
        int[] order = new int[count];
        uint[] keys = new uint[count];
        int[] scatter = new int[count];
        Order = order;
        _keys = keys;
        _scatter = scatter;
    }

    // Both dimensions and every coordinate type use the same temporary primitive buffers.
    // Every active key/order and scatter destination is written before it is read.
    internal Span<uint> HilbertKeys(int count) => _keys.AsSpan(0, count);
    internal Span<int> HilbertScatter(int count) => _scatter.AsSpan(0, count);
}
