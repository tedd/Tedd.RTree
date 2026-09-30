using System.Diagnostics;
using System.Globalization;
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using BenchmarkDotNet.Running;
using Tedd.RTree;

if (args is ["--profile"] or ["--profile-after"] or ["--disasm"])
{
    var fixture = new Fixture("Broad", false);
    var clock = Stopwatch.StartNew();
    long total = 0;
    while (clock.Elapsed.TotalSeconds < 12)
    {
        total += fixture.Query(args[0] == "--profile-after" ? fixture.AfterSearch : fixture.BeforeSearch);
        if (args[0] == "--disasm") total += fixture.Query(fixture.AfterSearch);
    }
    Console.WriteLine($"Broad-query checksum: {total}; elapsed: {clock.Elapsed}.");
}
else if (args is ["--screen", var output])
{
    Screening.Run(output);
}
else if (args is ["--focused-screen", var focusedOutput])
{
    foreach (var key in Screening.Variants.Keys.Where(k => k != "SpanCollector" && k != "ListCount").ToArray())
        Screening.Variants.Remove(key);
    Screening.Run(focusedOutput);
}
else if (args is ["--build-screen", var buildOutput]) Construction.Run(buildOutput);
else if (args is ["--generic-screen", var genericOutput]) GenericScreening.Run(genericOutput);
else if (args is ["--local-array-screen", var localArrayOutput]) GenericScreening.Run(localArrayOutput, true);
else BenchmarkSwitcher.FromAssembly(typeof(Fixture).Assembly).Run(args);

internal sealed class Fixture
{
    internal readonly SpatialEntry<int>[] Entries;
    internal readonly Rectangle[] Queries;
    internal readonly List<int> Results = [];
    internal readonly BaselineRTree<int> Before = new();
    internal readonly RTree<int> After = new();
    internal readonly LinearIndex Linear;
    internal readonly Func<Rectangle, List<int>, int> BeforeSearch;
    internal readonly Func<Rectangle, List<int>, int> AfterSearch;
    internal readonly Func<Rectangle, List<int>, int> SimdSearch;

    internal Fixture(string shape, bool clustered, int size = 10_000)
    {
        Random random = new(73211);
        Entries = new SpatialEntry<int>[size];
        for (int i = 0; i < size; i++)
        {
            double x = clustered ? i % 8 * 125 + random.NextDouble() * 30 : random.NextDouble() * 1000;
            double y = clustered ? i % 8 * 125 + random.NextDouble() * 30 : random.NextDouble() * 1000;
            Entries[i] = new(new(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        Queries = new Rectangle[64];
        for (int i = 0; i < Queries.Length; i++)
        {
            double x = random.NextDouble() * 1000, y = random.NextDouble() * 1000;
            double width = shape switch { "Point" => 0, "Small" => 20, "Medium" => 200, "Broad" => 1000, _ => 0 };
            Queries[i] = shape switch
            {
                "All" => new(-1, -1, 1010, 1010),
                "Miss" => new(2000, 2000, 2010, 2010),
                _ => new(x, y, x + width, y + width)
            };
        }
        Before.BulkLoad(Entries);
        After.BulkLoad(Entries);
        Linear = new(Entries.Select(e => e.Bounds).ToArray());
        BeforeSearch = Before.Search;
        AfterSearch = After.Search;
        SimdSearch = Linear.OneBitmap;
        Results.EnsureCapacity(size);
        Validate(Before.Search);
        Validate(After.Search);
        Validate(Linear.OneBitmap);
    }

    internal void Validate(Func<Rectangle, List<int>, int> search)
    {
        foreach (var query in Queries)
        {
            Results.Clear();
            int count = search(query, Results);
            var expected = Entries.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order();
            if (count != Results.Count || !Results.Order().SequenceEqual(expected))
                throw new InvalidOperationException("Independent linear oracle failed.");
        }
    }

    internal int Query(Func<Rectangle, List<int>, int> search)
    {
        int total = 0;
        foreach (var query in Queries)
        {
            Results.Clear();
            total += search(query, Results);
        }
        return total;
    }
}

internal static class Screening
{
    internal static readonly Dictionary<string, Func<SpatialEntry<int>[], Func<Rectangle, List<int>, int>>> Variants = [];

    internal static void Run(string output)
    {
        using StreamWriter writer = new(output);
        writer.WriteLine("Scenario,Variant,Round,Microseconds,AllocatedBytes,Checksum");
        foreach (bool clustered in new[] { false, true })
        foreach (string shape in new[] { "Point", "Small", "Medium", "Broad", "All", "Miss" })
        {
            var f = new Fixture(shape, clustered);
            List<(string Name, Func<int> Run)> variants =
            [
                ("Before", () => f.Query(f.BeforeSearch)),
                ("After", () => f.Query(f.AfterSearch)),
                ("SIMD", () => f.Query(f.SimdSearch))
            ];
            foreach (var candidate in Variants)
            {
                var search = candidate.Value(f.Entries);
                f.Validate(search);
                variants.Add((candidate.Key, () => f.Query(search)));
            }
            foreach (var variant in variants) Measure(variant.Run, 100);
            for (int round = 0; round < 9; round++)
            foreach (var variant in round % 2 == 0 ? variants : variants.AsEnumerable().Reverse())
            {
                var sample = Measure(variant.Run, 40);
                writer.WriteLine(FormattableString.Invariant($"{(clustered ? "Clustered" : "Uniform")}-{shape},{variant.Name},{round},{sample.Time},{sample.Allocation},{sample.Checksum}"));
                writer.Flush();
            }
            Console.WriteLine($"Screened {(clustered ? "Clustered" : "Uniform")}-{shape}.");
        }
    }

    internal static (double Time, double Allocation, long Checksum) Measure(Func<int> run, int milliseconds)
    {
        long allocation = GC.GetAllocatedBytesForCurrentThread();
        long start = Stopwatch.GetTimestamp(), elapsed;
        long checksum = 0;
        int n = 0;
        long target = Stopwatch.Frequency * milliseconds / 1000;
        do { checksum += run(); n++; elapsed = Stopwatch.GetTimestamp() - start; } while (elapsed < target);
        return (elapsed * 1_000_000.0 / Stopwatch.Frequency / n,
            (GC.GetAllocatedBytesForCurrentThread() - allocation) / (double)n, checksum);
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class TraversalBenchmarks
{
    [Params("Point", "Broad", "All")]
    public string Shape { get; set; } = "Point";
    private Fixture _fixture = null!;
    [GlobalSetup] public void Setup() => _fixture = new(Shape, false);
    [Benchmark(Baseline = true)] public int Before() => _fixture.Query(_fixture.BeforeSearch);
    [Benchmark] public int After() => _fixture.Query(_fixture.AfterSearch);
}
