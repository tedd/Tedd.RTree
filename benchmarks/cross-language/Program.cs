using System.Diagnostics;
using System.Globalization;
using Tedd.RTree;

CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
string mode = args[1];
string[] lines = File.ReadAllLines(args[0]);
int n = int.Parse(lines[0]);
Rectangle Read(string line)
{
    var v = line.Split(' ').Select(double.Parse).ToArray();
    return new(v[0], v[1], v[2], v[3]);
}
var bounds = lines.Skip(1).Take(n).Select(Read).ToArray();
var queries = lines.Skip(n + 1).Select(Read).ToArray();
var entries = bounds.Select((b, i) => new SpatialEntry<int>(b, i)).ToArray();
RTree<int> Build()
{
    var t = new RTree<int>(16);
    if (mode == "tedd-insert")
    {
        foreach (var e in entries)
            t.Insert(e.Bounds, e.Item);
    }
    else
        t.BulkLoad(entries);
    return t;
}
var tree = Build();
var buffer = new List<int>();
List<int> Search(Rectangle q)
{
    if (mode == "tedd-alloc")
        return tree.Search(q);
    buffer.Clear();
    tree.Search(q, buffer);
    return buffer;
}
for (int q = 0; q < queries.Length; q++)
{
    var expected = Enumerable.Range(0, n).Where(i => bounds[i].Intersects(queries[q])).ToArray();
    var actual = Search(queries[q]).Order().ToArray();
    if (!expected.SequenceEqual(actual))
        throw new Exception($"Result mismatch query {q}");
}
object? buildSink = null;
long sink = 0;
void Measure(string op, Func<long> action)
{
    long iterations = 1;
    double elapsed;
    do
    {
        var sw = Stopwatch.StartNew();
        for (long i = 0; i < iterations; i++)
            sink ^= action();
        elapsed = sw.Elapsed.TotalMilliseconds;
        if (elapsed < 100)
            iterations *= 2;
    } while (elapsed < 100);
    var timed = Stopwatch.StartNew();
    for (long i = 0; i < iterations; i++)
        sink ^= action();
    elapsed = timed.Elapsed.TotalMilliseconds;
    Console.WriteLine($"{op},{elapsed*1000/iterations:R},{iterations}");
}
Measure("build", () =>
                 {
                     buildSink = Build();
                     return ((RTree<int>)buildSink).Count;
                 });
for (int group = 0; group < 4; group++)
{
    int g = group;
    Measure($"query{g}", () =>
                         {
                             long sum = 0;
                             for (int q = g; q < queries.Length; q += 4)
                                 foreach (int id in Search(queries[q]))
                                     sum += id + 1;
                             return sum;
                         });
}
GC.KeepAlive(buildSink);
GC.KeepAlive(tree);
Console.Error.WriteLine($"validated={queries.Length};sink={sink}");
