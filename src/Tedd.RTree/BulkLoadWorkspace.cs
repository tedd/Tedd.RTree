using System.Numerics;

namespace Tedd.RTree;

/// <summary>Reusable scratch arrays for bulk loading one tree at a time.</summary>
/// <remarks>Do not use the same workspace concurrently. Its capacity remains allocated until the workspace is collected.</remarks>
public sealed class BulkLoadWorkspace
{
    internal int[] Order;
    internal double[] XCenters;
    internal double[] YCenters;
    internal BigInteger[]? XIntegerCenters;
    internal BigInteger[]? YIntegerCenters;
    internal BigInteger[]? ZIntegerCenters;
    internal double[]? ZCenters;

    /// <param name="capacity">Initial number of entries the workspace can accommodate.</param>
    public BulkLoadWorkspace(int capacity = 0)
    {
        if (capacity < 0) throw new ArgumentOutOfRangeException(nameof(capacity));
        Order = new int[capacity];
        XCenters = new double[capacity];
        YCenters = new double[capacity];
    }

    /// <summary>Number of entries that fit without growing scratch arrays.</summary>
    public int Capacity => Order.Length;

    internal void EnsureCapacity(int count)
    {
        if (Order.Length >= count) return;
        int[] order = new int[count];
        double[] xCenters = new double[count];
        double[] yCenters = new double[count];
        Order = order;
        XCenters = xCenters;
        YCenters = yCenters;
    }

    internal void EnsureIntegerCapacity(int count, bool threeDimensional)
    {
        if (XIntegerCenters is null || XIntegerCenters.Length < count)
            XIntegerCenters = new BigInteger[count];
        if (YIntegerCenters is null || YIntegerCenters.Length < count)
            YIntegerCenters = new BigInteger[count];
        if (threeDimensional && (ZIntegerCenters is null || ZIntegerCenters.Length < count))
            ZIntegerCenters = new BigInteger[count];
    }

    internal void EnsureZCapacity(int count)
    {
        if (ZCenters is null || ZCenters.Length < count)
            ZCenters = new double[count];
    }
}
