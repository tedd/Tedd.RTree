using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using Tedd.RTree;

CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
var lines = File.ReadAllLines(args[0]);
int n = int.Parse(lines[0]);
Rectangle Parse(string row) { var v = row.Split(' ').Select(double.Parse).ToArray(); return new(v[0], v[1], v[2], v[3]); }
Rectangle[] boxes = lines.Skip(1).Take(n).Select(Parse).ToArray();
Rectangle[] queries = lines.Skip(n + 1).Select(Parse).ToArray();
if (args.Length > 1 && args[1].StartsWith("native-")) { NativeBench.Run(boxes, queries, args[1]); return; }
var entries = boxes.Select((b, i) => new SpatialEntry<int>(b, i)).ToArray();
var list = new List<int>(n);
RTree<int> Build() { var t = new RTree<int>(); t.BulkLoad(entries); return t; }
var tree = Build();
for (int i = 0; i < queries.Length; i++)
{
    list.Clear(); tree.Search(queries[i], list);
    var expected = Enumerable.Range(0, n).Where(j => boxes[j].Intersects(queries[i])).ToArray();
    if (!list.Order().SequenceEqual(expected)) throw new Exception("Query result-set mismatch.");
}
long sink = 0;
RTree<int>? buildSink = null;
long Query(int group)
{
    long sum = 0;
    for (int j = group; j < queries.Length; j += 4)
    {
        list.Clear(); tree.Search(queries[j], list);
        foreach (int id in list) sum += id + 1;
    }
    return sum;
}
if (args.Length > 1 && args[1].StartsWith("profile-"))
{
    Console.WriteLine($"READY {Environment.ProcessId}"); Console.Out.Flush();
    var duration = Stopwatch.StartNew();
    while (duration.Elapsed.TotalSeconds < 45)
        if (args[1] == "profile-build") { buildSink = Build(); sink += buildSink.Count; }
        else for (int g = 0; g < 4; g++) sink ^= Query(g);
    GC.KeepAlive(buildSink); Console.WriteLine(sink); return;
}
if (args.Length > 1 && args[1] == "codegen")
{
    for (int g = 0; g < 4; g++) sink ^= Query(g);
    Console.WriteLine($"codegen={sink}"); return;
}
void Measure(string name, Func<long> action)
{
    int repetitions = 1;
    double Run() { var sw = Stopwatch.StartNew(); for (int i = 0; i < repetitions; i++) sink ^= action(); return sw.Elapsed.TotalMilliseconds; }
    while (Run() < 100) repetitions *= 2;
    long allocation = GC.GetAllocatedBytesForCurrentThread();
    double ms = Run(); allocation = GC.GetAllocatedBytesForCurrentThread() - allocation;
    Console.WriteLine($"{name},{ms * 1000 / repetitions:R},{repetitions},{(double)allocation / repetitions:R}");
}
if (args.Length < 2 || args[1] != "query-only") Measure("build", () => { buildSink = Build(); return buildSink.Count; });
if (args.Length > 1 && args[1] == "build-only")
{
    GC.KeepAlive(buildSink); Console.Error.WriteLine($"validated={queries.Length}"); return;
}
for (int g = 0; g < 4; g++) { int group = g; Measure($"query{g}", () => Query(group)); }
if (args.Length > 1 && args[1] == "query-only")
{
    Console.Error.WriteLine($"validated={queries.Length}"); return;
}
// Charge mutation itself separately and validate the resulting search path against a fresh oracle.
var moved = entries.Take(Math.Min(n, 1000)).ToArray();
long mutationAllocation = GC.GetAllocatedBytesForCurrentThread();
var mutation = Stopwatch.StartNew();
foreach (var e in moved)
{
    var b = new Rectangle(e.Bounds.MinX + 7, e.Bounds.MinY - 9, e.Bounds.MaxX + 7, e.Bounds.MaxY - 9);
    if (!tree.Update(e.Bounds, e.Item, b)) throw new Exception("Bulk-built update failed.");
    boxes[e.Item] = b;
}
Console.WriteLine($"mutation,{mutation.Elapsed.TotalMilliseconds * 1000:R},1,{GC.GetAllocatedBytesForCurrentThread() - mutationAllocation}");
for (int i = 0; i < queries.Length; i++)
{
    list.Clear(); tree.Search(queries[i], list);
    var expected = Enumerable.Range(0, n).Where(j => boxes[j].Intersects(queries[i])).ToArray();
    if (!list.Order().SequenceEqual(expected)) throw new Exception("Post-mutation result-set mismatch.");
}
for (int g = 0; g < 4; g++) { int group = g; Measure($"mutated{g}", () => Query(group)); }
GC.KeepAlive(tree); GC.KeepAlive(buildSink); Console.Error.WriteLine($"validated={queries.Length * 2};sink={sink}");
