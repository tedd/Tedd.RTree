using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using NetTopologySuite.Index.Strtree;
using Tedd.RTree;
using Rectangle = Tedd.RTree.Rectangle;

[ShortRunJob]
[MemoryDiagnoser]
public class PackageComparisonBenchmarks
{
    [Params(1_000, 10_000)] public int Size { get; set; }
    [Params("Uniform", "Clustered")] public string Distribution { get; set; } = "Uniform";
    [Params("Tedd.RTree", "RBush", "NetTopologySuite", "RTree", "Enyim.Collections.RTree")]
    public string Library { get; set; } = "Tedd.RTree";

    private IPreparedIndex _index = null!;

    [GlobalSetup]
    public void Setup()
    {
        var (bounds, queries) = PackageComparisonData.Create(Size, Distribution);
        _index = PackageIndexes.Prepare(Library, bounds, queries);
        PackageValidation.Check(_index, bounds, queries, Library);
    }

    [Benchmark] public object Build() => _index.Build();
    [Benchmark] public int Query64() => _index.QueryAll();
}

internal interface IPreparedIndex
{
    object Build();
    int QueryAll();
    IEnumerable<int> Search(int query);
}

// Geometry and adapter objects are prepared once; timed builds create a fresh index.
internal sealed class PreparedIndex<TTree, TQuery>(Func<TTree> build, TQuery[] queries,
    Func<TTree, TQuery, int> count, Func<TTree, TQuery, IEnumerable<int>> search) : IPreparedIndex
    where TTree : class
{
    private readonly TTree _tree = build();
    public object Build() => build();
    public int QueryAll()
    {
        int total = 0;
        foreach (TQuery query in queries) total += count(_tree, query);
        return total;
    }
    public IEnumerable<int> Search(int query) => search(_tree, queries[query]);
}

internal static class PackageComparisonData
{
    internal static (Rectangle[] Bounds, Rectangle[] Queries) Create(int size, string distribution)
    {
        Random random = new(73211);
        Rectangle[] bounds = new Rectangle[size];
        for (int i = 0; i < size; i++)
        {
            int x = distribution == "Clustered" ? (i % 8) * 125 + random.Next(30) : random.Next(1000);
            int y = distribution == "Clustered" ? (i % 8) * 125 + random.Next(30) : random.Next(1000);
            bounds[i] = new(x, y, x + random.Next(1, 6), y + random.Next(1, 6));
        }
        Rectangle[] queries = new Rectangle[64];
        for (int i = 0; i < queries.Length; i++)
        {
            int x = random.Next(1000), y = random.Next(1000);
            int width = (i % 4) switch { 0 => 0, 1 => 20, 2 => 200, _ => 1000 };
            queries[i] = new(x, y, x + width, y + width);
        }
        return (bounds, queries);
    }
}

internal static class PackageIndexes
{
    internal static readonly string[] Libraries =
        ["Tedd.RTree", "RBush", "NetTopologySuite", "RTree", "Enyim.Collections.RTree"];

    private sealed class BushItem(Rectangle bounds, int id) : RBush.ISpatialData
    {
        private readonly RBush.Envelope _bounds = new(bounds.MinX, bounds.MinY, bounds.MaxX, bounds.MaxY);
        public int Id { get; } = id;
        public ref readonly RBush.Envelope Envelope => ref _bounds;
    }

    private sealed class SharpItem(Rectangle bounds, int id) : SharpTrees.IBounded
    {
        private readonly SharpTrees.Bounds[] _bounds = SharpBounds(bounds);
        public int Id { get; } = id;
        public SharpTrees.Bounds[] GetBounds() => _bounds;
        public bool IsEqual(SharpTrees.IBounded other) => other is SharpItem item && item.Id == Id;
    }

    private static SharpTrees.Bounds[] SharpBounds(Rectangle r) =>
        [new(r.MinX, r.MaxX), new(r.MinY, r.MaxY)];

    internal static IPreparedIndex Prepare(string library, Rectangle[] bounds, Rectangle[] queries)
    {
        switch (library)
        {
            case "Tedd.RTree":
                SpatialEntry<int>[] entries = bounds.Select((b, i) => new SpatialEntry<int>(b, i)).ToArray();
                return new PreparedIndex<Tedd.RTree.RTree<int>, Rectangle>(() =>
                {
                    Tedd.RTree.RTree<int> tree = new(16);
                    tree.BulkLoad(entries);
                    return tree;
                }, queries, (t, q) => t.Search(q).Count, (t, q) => t.Search(q));
            case "RBush":
                BushItem[] items = bounds.Select((b, i) => new BushItem(b, i)).ToArray();
                RBush.Envelope[] bushQueries = queries.Select(q => new RBush.Envelope(q.MinX, q.MinY, q.MaxX, q.MaxY)).ToArray();
                return new PreparedIndex<RBush.RBush<BushItem>, RBush.Envelope>(() =>
                {
                    RBush.RBush<BushItem> tree = new(16);
                    tree.BulkLoad(items);
                    return tree;
                }, bushQueries, (t, q) => t.Search(q).Count, (t, q) => t.Search(q).Select(i => i.Id));
            case "NetTopologySuite":
                var ntsBounds = bounds.Select(q => new NetTopologySuite.Geometries.Envelope(q.MinX, q.MaxX, q.MinY, q.MaxY)).ToArray();
                var ntsQueries = queries.Select(q => new NetTopologySuite.Geometries.Envelope(q.MinX, q.MaxX, q.MinY, q.MaxY)).ToArray();
                return new PreparedIndex<STRtree<int>, NetTopologySuite.Geometries.Envelope>(() =>
                {
                    STRtree<int> tree = new(16);
                    for (int i = 0; i < ntsBounds.Length; i++) tree.Insert(ntsBounds[i], i);
                    tree.Build();
                    return tree;
                }, ntsQueries, (t, q) => t.Query(q).Count, (t, q) => t.Query(q));
            case "RTree":
                // This package indexes float coordinates in 3D; z=0 embeds the exact 2D fixture.
                var legacyBounds = bounds.Select(q => new global::RTree.Rectangle((float)q.MinX, (float)q.MinY, (float)q.MaxX, (float)q.MaxY, 0, 0)).ToArray();
                var legacyQueries = queries.Select(q => new global::RTree.Rectangle((float)q.MinX, (float)q.MinY, (float)q.MaxX, (float)q.MaxY, 0, 0)).ToArray();
                return new PreparedIndex<global::RTree.RTree<int>, global::RTree.Rectangle>(() =>
                {
                    global::RTree.RTree<int> tree = new(16, 6);
                    for (int i = 0; i < legacyBounds.Length; i++) tree.Add(legacyBounds[i], i);
                    return tree;
                }, legacyQueries, (t, q) => t.Intersects(q).Count, (t, q) => t.Intersects(q));
            case "Enyim.Collections.RTree":
                var nodes = bounds.Select((q, i) => new Enyim.Collections.RTreeNode<int>(i,
                    new Enyim.Collections.Envelope((int)q.MinX, (int)q.MinY, (int)q.MaxX, (int)q.MaxY))).ToArray();
                var enyimQueries = queries.Select(q => new Enyim.Collections.Envelope((int)q.MinX, (int)q.MinY, (int)q.MaxX, (int)q.MaxY)).ToArray();
                return new PreparedIndex<Enyim.Collections.RTree<int>, Enyim.Collections.Envelope>(() =>
                {
                    Enyim.Collections.RTree<int> tree = new(16);
                    // Load sorts its input list. Include a fresh working copy in every timed build.
                    tree.Load(new List<Enyim.Collections.RTreeNode<int>>(nodes));
                    return tree;
                }, enyimQueries, (t, q) => t.Search(q).Count, (t, q) => t.Search(q).Select(i => i.Data));
            case "SharpTrees":
                SharpItem[] sharpItems = bounds.Select((q, i) => new SharpItem(q, i)).ToArray();
                var sharpQueries = queries.Select(SharpBounds).ToArray();
                return new PreparedIndex<SharpTrees.RTree<SharpItem>, SharpTrees.Bounds[]>(() =>
                {
                    // The package recommends small nodes because its exhaustive split is exponential.
                    SharpTrees.RTree<SharpItem> tree = new(4, 2, SharpTrees.NodeSplitStrategy.Exhaustive);
                    foreach (SharpItem item in sharpItems)
                        if (!tree.Add(item)) throw new InvalidOperationException("SharpTrees rejected a unique ID.");
                    return tree;
                }, sharpQueries, (t, q) => t.SearchIntersections(q).Count, (t, q) => t.SearchIntersections(q).Select(i => i.Id));
            default: throw new ArgumentOutOfRangeException(nameof(library), library, "Unknown package.");
        }
    }
}

internal static class PackageValidation
{
    internal static void Check(IPreparedIndex index, Rectangle[] bounds, Rectangle[] queries, string label)
    {
        int total = 0;
        for (int q = 0; q < queries.Length; q++)
        {
            int[] expected = Enumerable.Range(0, bounds.Length).Where(i => bounds[i].Intersects(queries[q])).ToArray();
            int[] actual = index.Search(q).Order().ToArray();
            if (!actual.SequenceEqual(expected))
                throw new InvalidOperationException($"{label}, query {q} {queries[q]}: result IDs differ from brute force (expected {expected.Length}, got {actual.Length}); missing=[{string.Join(',', expected.Except(actual))}], extra=[{string.Join(',', actual.Except(expected))}].");
            total += expected.Length;
        }
        if (index.QueryAll() != total) throw new InvalidOperationException($"{label}: timed query counts differ.");
    }

    internal static void Run()
    {
        foreach (string library in PackageIndexes.Libraries)
        {
            foreach (int size in new[] { 1_000, 10_000 })
            foreach (string distribution in new[] { "Uniform", "Clustered" })
            {
                var (bounds, queries) = PackageComparisonData.Create(size, distribution);
                Check(PackageIndexes.Prepare(library, bounds, queries), bounds, queries, $"{library}/{size}/{distribution}");
            }
            Rectangle[] boundary = [new(-10, -5, 0, 5), new(0, 5, 10, 15), new(0, 5, 10, 15), new(20, 30, 21, 31)];
            Rectangle[] boundaryQueries = [new(0, 5, 0, 5), new(-100, -100, 100, 100), new(100, 100, 101, 101), new(21, 31, 21, 31)];
            foreach (Rectangle[] bounds in new[] { Array.Empty<Rectangle>(), boundary, boundary.Reverse().ToArray() })
                Check(PackageIndexes.Prepare(library, bounds, boundaryQueries), bounds, boundaryQueries, $"{library}/boundary");
            Console.WriteLine($"{library}: differential and boundary validation passed.");
        }
    }
}
