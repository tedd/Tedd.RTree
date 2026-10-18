using System.Diagnostics;
using System.Globalization;
using NetTopologySuite.Index;
using NetTopologySuite.Index.Strtree;
using Tedd.RTree;
using Rectangle = Tedd.RTree.Rectangle;

CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
Rectangle Parse(string row) { var v = row.Split(' ').Select(double.Parse).ToArray(); return new(v[0], v[1], v[2], v[3]); }
var lines = File.ReadAllLines(args[0]);
int n = int.Parse(lines[0]);
Rectangle[] boxes = lines.Skip(1).Take(n).Select(Parse).ToArray();
Rectangle[] queries = lines.Skip(n + 1).Select(Parse).ToArray();
var index = Indexes.Prepare(args[1], boxes, queries);
long expectedSink = 0;
for (int q = 0; q < queries.Length; q++)
{
    var expected = Enumerable.Range(0, n).Where(i => boxes[i].Intersects(queries[q])).ToArray();
    if (!index.Results(q).Order().SequenceEqual(expected)) throw new Exception($"Result IDs differ: query {q}");
    long sum = expected.Sum(i => (long)i + 1);
    if (index.Query(q) != sum) throw new Exception($"Timed checksum differs: query {q}");
    expectedSink += sum;
}
if (args.Length > 2 && args[2] == "validate") { Console.Error.WriteLine($"validated={queries.Length};expected={expectedSink}"); return; }
long sink = 0;
object? buildSink = null;
void Measure(string name, Func<long> action)
{
    int repetitions = 1;
    double Run() { var sw = Stopwatch.StartNew(); for (int i = 0; i < repetitions; i++) sink ^= action(); return sw.Elapsed.TotalMilliseconds; }
    while (Run() < 100) repetitions = checked(repetitions * 2);
    long allocation = GC.GetAllocatedBytesForCurrentThread();
    double ms = Run(); allocation = GC.GetAllocatedBytesForCurrentThread() - allocation;
    Console.WriteLine($"{name},{ms * 1000 / repetitions:R},{repetitions},{(double)allocation / repetitions:R}");
}
Measure("build", () => { buildSink = index.Build(); return n; });
for (int g = 0; g < 4; g++)
{
    int group = g;
    Measure($"query{g}", () => { long sum = 0; for (int q = group; q < queries.Length; q += 4) sum += index.Query(q); return sum; });
}
GC.KeepAlive(buildSink); GC.KeepAlive(index);
Console.Error.WriteLine($"validated={queries.Length};expected={expectedSink};sink={sink}");

internal interface IIndex { object Build(); long Query(int q); IEnumerable<int> Results(int q); }
internal sealed class Prepared<TTree, TQuery>(Func<TTree> build, TQuery[] queries,
    Func<TTree, TQuery, long> consume, Func<TTree, TQuery, IEnumerable<int>> search) : IIndex where TTree : class
{
    private readonly TTree tree = build();
    public object Build() => build();
    public long Query(int q) => consume(tree, queries[q]);
    public IEnumerable<int> Results(int q) => search(tree, queries[q]);
}
internal static class Indexes
{
    private sealed class BushItem(Rectangle bounds, int id) : RBush.ISpatialData
    {
        private readonly RBush.Envelope envelope = new(bounds.MinX, bounds.MinY, bounds.MaxX, bounds.MaxY);
        internal int Id { get; } = id;
        public ref readonly RBush.Envelope Envelope => ref envelope;
    }
    private sealed class SumVisitor : IItemVisitor<int>
    {
        internal long Sum;
        public void VisitItem(int item) => Sum += item + 1;
    }
    private sealed class ListVisitor : IItemVisitor<int>
    {
        internal readonly List<int> Items = [];
        public void VisitItem(int item) => Items.Add(item);
    }
    internal static IIndex Prepare(string mode, Rectangle[] boxes, Rectangle[] queries)
    {
        switch (mode)
        {
            case "candidate":
                var entries = boxes.Select((b, i) => new SpatialEntry<int>(b, i)).ToArray();
                var result = new List<int>(boxes.Length);
                return new Prepared<Tedd.RTree.RTree<int>, Rectangle>(() => {
                    var t = new Tedd.RTree.RTree<int>(16); t.BulkLoad(entries); return t;
                }, queries, (t, q) => { result.Clear(); t.Search(q, result); long sum = 0; foreach (int id in result) sum += id + 1; return sum; },
                    (t, q) => t.Search(q));
            case "rbush":
                var items = boxes.Select((b, i) => new BushItem(b, i)).ToArray();
                var bushQueries = queries.Select(b => new RBush.Envelope(b.MinX, b.MinY, b.MaxX, b.MaxY)).ToArray();
                return new Prepared<RBush.RBush<BushItem>, RBush.Envelope>(() => {
                    var t = new RBush.RBush<BushItem>(16); t.BulkLoad(items); return t;
                }, bushQueries, (t, q) => { long sum = 0; foreach (var item in t.Search(q)) sum += item.Id + 1; return sum; },
                    (t, q) => t.Search(q).Select(item => item.Id));
            case "nts-list":
            case "nts-visitor":
                var ntsBounds = boxes.Select(b => new NetTopologySuite.Geometries.Envelope(b.MinX, b.MaxX, b.MinY, b.MaxY)).ToArray();
                var ntsQueries = queries.Select(b => new NetTopologySuite.Geometries.Envelope(b.MinX, b.MaxX, b.MinY, b.MaxY)).ToArray();
                var visitor = new SumVisitor();
                return new Prepared<STRtree<int>, NetTopologySuite.Geometries.Envelope>(() => {
                    var t = new STRtree<int>(16); for (int i = 0; i < ntsBounds.Length; i++) t.Insert(ntsBounds[i], i); t.Build(); return t;
                }, ntsQueries, mode == "nts-list" ? (t, q) => { long sum = 0; foreach (int id in t.Query(q)) sum += id + 1; return sum; }
                    : (t, q) => { visitor.Sum = 0; t.Query(q, visitor); return visitor.Sum; },
                    (t, q) => { if (mode == "nts-list") return t.Query(q); var collect = new ListVisitor(); t.Query(q, collect); return collect.Items; });
            case "rtree":
                var oldBounds = boxes.Select(b => new global::RTree.Rectangle((float)b.MinX, (float)b.MinY, (float)b.MaxX, (float)b.MaxY, 0, 0)).ToArray();
                var oldQueries = queries.Select(b => new global::RTree.Rectangle((float)b.MinX, (float)b.MinY, (float)b.MaxX, (float)b.MaxY, 0, 0)).ToArray();
                return new Prepared<global::RTree.RTree<int>, global::RTree.Rectangle>(() => {
                    var t = new global::RTree.RTree<int>(16, 6); for (int i = 0; i < oldBounds.Length; i++) t.Add(oldBounds[i], i); return t;
                }, oldQueries, (t, q) => { long sum = 0; foreach (int id in t.Intersects(q)) sum += id + 1; return sum; }, (t, q) => t.Intersects(q));
            case "enyim":
                var nodes = boxes.Select((b, i) => new Enyim.Collections.RTreeNode<int>(i, new Enyim.Collections.Envelope((int)b.MinX, (int)b.MinY, (int)b.MaxX, (int)b.MaxY))).ToArray();
                var enyimQueries = queries.Select(b => new Enyim.Collections.Envelope((int)b.MinX, (int)b.MinY, (int)b.MaxX, (int)b.MaxY)).ToArray();
                return new Prepared<Enyim.Collections.RTree<int>, Enyim.Collections.Envelope>(() => {
                    var t = new Enyim.Collections.RTree<int>(16); t.Load(new List<Enyim.Collections.RTreeNode<int>>(nodes)); return t;
                }, enyimQueries, (t, q) => { long sum = 0; foreach (var item in t.Search(q)) sum += item.Data + 1; return sum; }, (t, q) => t.Search(q).Select(item => item.Data));
            default: throw new ArgumentException("Unknown library");
        }
    }
}
