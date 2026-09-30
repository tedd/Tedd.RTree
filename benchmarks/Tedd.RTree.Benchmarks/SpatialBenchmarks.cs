using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using NetTopologySuite.Index.Strtree;
using Tedd.RTree;
using NEnvelope = NetTopologySuite.Geometries.Envelope;
using BEnvelope = RBush.Envelope;

[ShortRunJob]
[MemoryDiagnoser]
public class SpatialBenchmarks
{
    private sealed class Item(Rectangle bounds, int id) : RBush.ISpatialData
    {
        private readonly BEnvelope _envelope = new(bounds.MinX, bounds.MinY, bounds.MaxX, bounds.MaxY);
        public int Id { get; } = id;
        public ref readonly BEnvelope Envelope => ref _envelope;
    }

    [Params(1_000, 10_000)]
    public int Size { get; set; }

    [Params("Uniform", "Clustered")]
    public string Distribution { get; set; } = "Uniform";

    private Rectangle[] _rectangles = null!;
    private SpatialEntry<int>[] _bulkItems = null!;
    private Item[] _items = null!;
    private NEnvelope[] _ntsBounds = null!;
    private Rectangle[] _queries = null!;
    private BEnvelope[] _rbushQueries = null!;
    private NEnvelope[] _ntsQueries = null!;
    private RTree<int> _tree = null!;
    private RTree<int> _bulkTree = null!;
    private RBush.RBush<Item> _rbush = null!;
    private RBush.RBush<Item> _rbushBulk = null!;
    private STRtree<int> _nts = null!;
    private readonly List<int> _results = [];

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _rectangles = new Rectangle[Size];
        _bulkItems = new SpatialEntry<int>[Size];
        _items = new Item[Size];
        _ntsBounds = new NEnvelope[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = Distribution == "Clustered"
                ? (i % 8) * 125 + random.NextDouble() * 30
                : random.NextDouble() * 1000;
            double y = Distribution == "Clustered"
                ? (i % 8) * 125 + random.NextDouble() * 30
                : random.NextDouble() * 1000;
            Rectangle bounds = new(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            _rectangles[i] = bounds;
            _bulkItems[i] = new SpatialEntry<int>(bounds, i);
            _items[i] = new Item(bounds, i);
            _ntsBounds[i] = new NEnvelope(bounds.MinX, bounds.MaxX, bounds.MinY, bounds.MaxY);
        }

        _queries = new Rectangle[64];
        _rbushQueries = new BEnvelope[64];
        _ntsQueries = new NEnvelope[64];
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            double width = (i % 4) switch { 0 => 0, 1 => 20, 2 => 200, _ => 1000 };
            Rectangle query = new(x, y, x + width, y + width);
            _queries[i] = query;
            _rbushQueries[i] = new BEnvelope(query.MinX, query.MinY, query.MaxX, query.MaxY);
            _ntsQueries[i] = new NEnvelope(query.MinX, query.MaxX, query.MinY, query.MaxY);
        }

        _tree = CreateTedd();
        _bulkTree = CreateTeddBulk();
        _rbush = CreateRBush();
        _rbushBulk = CreateRBushBulk();
        _nts = CreateNts();
        for (int q = 0; q < _queries.Length; q++)
        {
            int expected = 0;
            foreach (Rectangle item in _rectangles)
                if (item.Intersects(_queries[q])) expected++;
            _results.Clear();
            int ours = _tree.Search(_queries[q], _results);
            _results.Clear();
            int oursBulk = _bulkTree.Search(_queries[q], _results);
            int rbush = _rbush.Search(_rbushQueries[q]).Count();
            int rbushBulk = _rbushBulk.Search(_rbushQueries[q]).Count();
            int nts = _nts.Query(_ntsQueries[q]).Count;
            if (ours != expected || oursBulk != expected || rbush != expected || rbushBulk != expected || nts != expected)
                throw new InvalidOperationException($"Query {q}: expected {expected}, got {ours}/{oursBulk}/{rbush}/{rbushBulk}/{nts}.");
        }
    }

    private RTree<int> CreateTedd()
    {
        RTree<int> tree = new(16);
        for (int i = 0; i < _rectangles.Length; i++)
            tree.Insert(_rectangles[i], i);
        return tree;
    }

    private RTree<int> CreateTeddBulk()
    {
        RTree<int> tree = new(16);
        tree.BulkLoad(_bulkItems);
        return tree;
    }

    private RBush.RBush<Item> CreateRBush()
    {
        RBush.RBush<Item> tree = new(maxEntries: 16);
        foreach (Item item in _items) tree.Insert(item);
        return tree;
    }

    private RBush.RBush<Item> CreateRBushBulk()
    {
        RBush.RBush<Item> tree = new(maxEntries: 16);
        tree.BulkLoad(_items);
        return tree;
    }

    private STRtree<int> CreateNts()
    {
        STRtree<int> tree = new(16);
        for (int i = 0; i < _ntsBounds.Length; i++)
            tree.Insert(_ntsBounds[i], i);
        tree.Build();
        return tree;
    }

    [Benchmark(Baseline = true)]
    public int Build_Tedd() => CreateTedd().Count;

    [Benchmark]
    public int Build_Tedd_Bulk() => CreateTeddBulk().Count;

    [Benchmark]
    public int Build_RBush() => CreateRBush().Count;

    [Benchmark]
    public int Build_RBush_Bulk() => CreateRBushBulk().Count;

    [Benchmark]
    public int Build_Nts() => CreateNts().Count;

    [Benchmark]
    public int Query_Tedd()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _tree.Search(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int Query_Tedd_Bulk()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            total += _bulkTree.Search(query, _results);
        }
        return total;
    }

    [Benchmark]
    public int Query_Tedd_Allocating()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
            total += _tree.Search(query).Count;
        return total;
    }

    [Benchmark]
    public int Query_Tedd_Bulk_Allocating()
    {
        int total = 0;
        foreach (Rectangle query in _queries)
            total += _bulkTree.Search(query).Count;
        return total;
    }

    [Benchmark]
    public int Query_RBush()
    {
        int total = 0;
        foreach (BEnvelope query in _rbushQueries)
            total += _rbush.Search(query).Count();
        return total;
    }

    [Benchmark]
    public int Query_RBush_Bulk()
    {
        int total = 0;
        foreach (BEnvelope query in _rbushQueries)
            total += _rbushBulk.Search(query).Count();
        return total;
    }

    [Benchmark]
    public int Query_Nts()
    {
        int total = 0;
        foreach (NEnvelope query in _ntsQueries)
            total += _nts.Query(query).Count;
        return total;
    }
}
