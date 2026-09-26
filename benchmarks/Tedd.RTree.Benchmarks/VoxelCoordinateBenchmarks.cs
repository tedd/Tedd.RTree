using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using Tedd.RTree;

[MemoryDiagnoser]
[SimpleJob(launchCount: 1, warmupCount: 5, iterationCount: 10)]
public class VoxelCoordinateBenchmarks
{
    private RTree<int> _legacy2D = null!;
    private RTree2D<int, int> _int2D = null!;
    private RTree2D<long, int> _long2D = null!;
    private RTree2D<float, int> _float2D = null!;
    private RTree2D<double, int> _double2D = null!;
    private RTree3D<int, int> _int3D = null!;
    private RTree3D<long, int> _long3D = null!;
    private RTree3D<float, int> _float3D = null!;
    private RTree3D<double, int> _double3D = null!;
    private Rectangle[] _legacyQueries = null!;
    private Rectangle2D<int>[] _intQueries2D = null!;
    private Rectangle2D<long>[] _longQueries2D = null!;
    private Rectangle2D<float>[] _floatQueries2D = null!;
    private Rectangle2D<double>[] _doubleQueries2D = null!;
    private Box<int>[] _intQueries3D = null!;
    private Box<long>[] _longQueries3D = null!;
    private Box<float>[] _floatQueries3D = null!;
    private Box<double>[] _doubleQueries3D = null!;
    private readonly List<int> _results = new();

    [Params("Point", "Region")]
    public string QueryKind { get; set; } = "Point";

    [GlobalSetup]
    public void Setup()
    {
        const int size = 10_000;
        Random random = new(73211);
        var legacyEntries = new SpatialEntry<int>[size];
        var intEntries2D = new SpatialEntry2D<int, int>[size];
        var longEntries2D = new SpatialEntry2D<long, int>[size];
        var floatEntries2D = new SpatialEntry2D<float, int>[size];
        var doubleEntries2D = new SpatialEntry2D<double, int>[size];
        var intEntries3D = new SpatialEntry3D<int, int>[size];
        var longEntries3D = new SpatialEntry3D<long, int>[size];
        var floatEntries3D = new SpatialEntry3D<float, int>[size];
        var doubleEntries3D = new SpatialEntry3D<double, int>[size];
        for (int i = 0; i < size; i++)
        {
            int x = random.Next(-500, 500), y = random.Next(-500, 500), z = random.Next(-500, 500);
            legacyEntries[i] = new(new Rectangle(x, y, x + 1, y + 1), i);
            intEntries2D[i] = new(new Rectangle2D<int>(x, y, x + 1, y + 1), i);
            longEntries2D[i] = new(new Rectangle2D<long>(x, y, x + 1, y + 1), i);
            floatEntries2D[i] = new(new Rectangle2D<float>(x, y, x + 1, y + 1), i);
            doubleEntries2D[i] = new(new Rectangle2D<double>(x, y, x + 1, y + 1), i);
            intEntries3D[i] = new(new Box<int>(x, y, z, x + 1, y + 1, z + 1), i);
            longEntries3D[i] = new(new Box<long>(x, y, z, x + 1, y + 1, z + 1), i);
            floatEntries3D[i] = new(new Box<float>(x, y, z, x + 1, y + 1, z + 1), i);
            doubleEntries3D[i] = new(new Box<double>(x, y, z, x + 1, y + 1, z + 1), i);
        }

        _legacy2D = new(); _legacy2D.BulkLoad(legacyEntries);
        _int2D = new(); _int2D.BulkLoad(intEntries2D);
        _long2D = new(); _long2D.BulkLoad(longEntries2D);
        _float2D = new(); _float2D.BulkLoad(floatEntries2D);
        _double2D = new(); _double2D.BulkLoad(doubleEntries2D);
        _int3D = new(); _int3D.BulkLoad(intEntries3D);
        _long3D = new(); _long3D.BulkLoad(longEntries3D);
        _float3D = new(); _float3D.BulkLoad(floatEntries3D);
        _double3D = new(); _double3D.BulkLoad(doubleEntries3D);

        _legacyQueries = new Rectangle[64];
        _intQueries2D = new Rectangle2D<int>[64];
        _longQueries2D = new Rectangle2D<long>[64];
        _floatQueries2D = new Rectangle2D<float>[64];
        _doubleQueries2D = new Rectangle2D<double>[64];
        _intQueries3D = new Box<int>[64];
        _longQueries3D = new Box<long>[64];
        _floatQueries3D = new Box<float>[64];
        _doubleQueries3D = new Box<double>[64];
        int width = QueryKind == "Point" ? 0 : 100;
        for (int i = 0; i < 64; i++)
        {
            int x = random.Next(-500, 500), y = random.Next(-500, 500), z = random.Next(-500, 500);
            _legacyQueries[i] = new(x, y, x + width, y + width);
            _intQueries2D[i] = new(x, y, x + width, y + width);
            _longQueries2D[i] = new(x, y, x + width, y + width);
            _floatQueries2D[i] = new(x, y, x + width, y + width);
            _doubleQueries2D[i] = new(x, y, x + width, y + width);
            _intQueries3D[i] = new(x, y, z, x + width, y + width, z + width);
            _longQueries3D[i] = new(x, y, z, x + width, y + width, z + width);
            _floatQueries3D[i] = new(x, y, z, x + width, y + width, z + width);
            _doubleQueries3D[i] = new(x, y, z, x + width, y + width, z + width);
        }

        int expected2D = Query(_legacy2D, _legacyQueries);
        if (Query(_int2D, _intQueries2D) != expected2D ||
            Query(_long2D, _longQueries2D) != expected2D ||
            Query(_float2D, _floatQueries2D) != expected2D ||
            Query(_double2D, _doubleQueries2D) != expected2D)
            throw new InvalidOperationException("2D coordinate variants disagree.");
        int expected3D = Query(_int3D, _intQueries3D);
        if (Query(_long3D, _longQueries3D) != expected3D ||
            Query(_float3D, _floatQueries3D) != expected3D ||
            Query(_double3D, _doubleQueries3D) != expected3D)
            throw new InvalidOperationException("3D coordinate variants disagree.");
    }

    private int Query(RTree<int> tree, Rectangle[] queries)
    {
        int matches = 0;
        foreach (var query in queries)
        {
            _results.Clear();
            matches += tree.Search(query, _results);
        }
        return matches;
    }

    private int Query<TCoordinate>(RTree2D<TCoordinate, int> tree, Rectangle2D<TCoordinate>[] queries)
        where TCoordinate : struct, System.Numerics.INumber<TCoordinate>
    {
        int matches = 0;
        foreach (var query in queries)
        {
            _results.Clear();
            matches += tree.Search(query, _results);
        }
        return matches;
    }

    private int Query<TCoordinate>(RTree3D<TCoordinate, int> tree, Box<TCoordinate>[] queries)
        where TCoordinate : struct, System.Numerics.INumber<TCoordinate>
    {
        int matches = 0;
        foreach (var query in queries)
        {
            _results.Clear();
            matches += tree.Search(query, _results);
        }
        return matches;
    }

    [Benchmark(Baseline = true)] public int LegacyDouble2D() => Query(_legacy2D, _legacyQueries);
    [Benchmark] public int Int2D() => Query(_int2D, _intQueries2D);
    [Benchmark] public int Long2D() => Query(_long2D, _longQueries2D);
    [Benchmark] public int Float2D() => Query(_float2D, _floatQueries2D);
    [Benchmark] public int GenericDouble2D() => Query(_double2D, _doubleQueries2D);
    [Benchmark] public int Int3D() => Query(_int3D, _intQueries3D);
    [Benchmark] public int Long3D() => Query(_long3D, _longQueries3D);
    [Benchmark] public int Float3D() => Query(_float3D, _floatQueries3D);
    [Benchmark] public int Double3D() => Query(_double3D, _doubleQueries3D);
}

[MemoryDiagnoser]
[SimpleJob(launchCount: 1, warmupCount: 3, iterationCount: 5)]
public class VoxelBuildBenchmarks
{
    private SpatialEntry<int>[] _legacy2D = null!;
    private SpatialEntry2D<int, int>[] _int2D = null!;
    private SpatialEntry2D<long, int>[] _long2D = null!;
    private SpatialEntry2D<float, int>[] _float2D = null!;
    private SpatialEntry2D<double, int>[] _double2D = null!;
    private SpatialEntry3D<int, int>[] _int3D = null!;
    private SpatialEntry3D<long, int>[] _long3D = null!;
    private SpatialEntry3D<float, int>[] _float3D = null!;
    private SpatialEntry3D<double, int>[] _double3D = null!;

    [GlobalSetup]
    public void Setup()
    {
        const int size = 10_000;
        Random random = new(73211);
        _legacy2D = new SpatialEntry<int>[size];
        _int2D = new SpatialEntry2D<int, int>[size];
        _long2D = new SpatialEntry2D<long, int>[size];
        _float2D = new SpatialEntry2D<float, int>[size];
        _double2D = new SpatialEntry2D<double, int>[size];
        _int3D = new SpatialEntry3D<int, int>[size];
        _long3D = new SpatialEntry3D<long, int>[size];
        _float3D = new SpatialEntry3D<float, int>[size];
        _double3D = new SpatialEntry3D<double, int>[size];
        for (int i = 0; i < size; i++)
        {
            int x = random.Next(-500, 500), y = random.Next(-500, 500), z = random.Next(-500, 500);
            _legacy2D[i] = new(new Rectangle(x, y, x + 1, y + 1), i);
            _int2D[i] = new(new Rectangle2D<int>(x, y, x + 1, y + 1), i);
            _long2D[i] = new(new Rectangle2D<long>(x, y, x + 1, y + 1), i);
            _float2D[i] = new(new Rectangle2D<float>(x, y, x + 1, y + 1), i);
            _double2D[i] = new(new Rectangle2D<double>(x, y, x + 1, y + 1), i);
            _int3D[i] = new(new Box<int>(x, y, z, x + 1, y + 1, z + 1), i);
            _long3D[i] = new(new Box<long>(x, y, z, x + 1, y + 1, z + 1), i);
            _float3D[i] = new(new Box<float>(x, y, z, x + 1, y + 1, z + 1), i);
            _double3D[i] = new(new Box<double>(x, y, z, x + 1, y + 1, z + 1), i);
        }
    }

    [Benchmark(Baseline = true)]
    public int LegacyDouble2D() { RTree<int> tree = new(); tree.BulkLoad(_legacy2D); return tree.Count; }
    [Benchmark]
    public int Int2D() { RTree2D<int, int> tree = new(); tree.BulkLoad(_int2D); return tree.Count; }
    [Benchmark]
    public int Long2D() { RTree2D<long, int> tree = new(); tree.BulkLoad(_long2D); return tree.Count; }
    [Benchmark]
    public int Float2D() { RTree2D<float, int> tree = new(); tree.BulkLoad(_float2D); return tree.Count; }
    [Benchmark]
    public int GenericDouble2D() { RTree2D<double, int> tree = new(); tree.BulkLoad(_double2D); return tree.Count; }
    [Benchmark]
    public int Int3D() { RTree3D<int, int> tree = new(); tree.BulkLoad(_int3D); return tree.Count; }
    [Benchmark]
    public int Long3D() { RTree3D<long, int> tree = new(); tree.BulkLoad(_long3D); return tree.Count; }
    [Benchmark]
    public int Float3D() { RTree3D<float, int> tree = new(); tree.BulkLoad(_float3D); return tree.Count; }
    [Benchmark]
    public int Double3D() { RTree3D<double, int> tree = new(); tree.BulkLoad(_double3D); return tree.Count; }
}
