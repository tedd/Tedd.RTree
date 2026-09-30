using System.Numerics;
using Tedd.RTree;

internal static class GenericScreening
{
    internal static void Run(string output, bool localArray = false)
    {
        using var writer = new StreamWriter(output);
        writer.WriteLine("Scenario,Variant,Round,Microseconds,AllocatedBytes,Checksum");
        Run<int>(writer, localArray); Run<long>(writer, localArray); Run<float>(writer, localArray); Run<double>(writer, localArray);
    }

    private static void Run<C>(StreamWriter writer, bool localArray) where C : struct, INumber<C>
    {
        static C N(int value) => C.CreateChecked(value);
        var entries2 = new SpatialEntry2D<C, int>[10_000];
        var entries3 = new SpatialEntry3D<C, int>[10_000];
        Random random = new(73211);
        for (int i = 0; i < entries2.Length; i++)
        {
            int x = random.Next(1000), y = random.Next(1000), z = random.Next(1000);
            entries2[i] = new(new(N(x), N(y), N(x + 3), N(y + 3)), i);
            entries3[i] = new(new(N(x), N(y), N(z), N(x + 3), N(y + 3), N(z + 3)), i);
        }
        var before2 = new BaselineRTree2D<C, int>(); before2.BulkLoad(entries2);
        var after2 = new RTree2D<C, int>(); after2.BulkLoad(entries2);
        var before3 = new BaselineRTree3D<C, int>(); before3.BulkLoad(entries3);
        var after3 = new RTree3D<C, int>(); after3.BulkLoad(entries3);
        var local2 = new LocalArrayRTree2D<C, int>(); local2.BulkLoad(entries2);
        var local3 = new LocalArrayRTree3D<C, int>(); local3.BulkLoad(entries3);
        Func<Rectangle2D<C>, List<int>, int> after2Search = localArray ? local2.Search : after2.Search;
        Func<Box<C>, List<int>, int> after3Search = localArray ? local3.Search : after3.Search;
        List<int> results = new(10_000);
        foreach (string shape in new[] { "Point", "Small", "Broad", "All" })
        {
            var queries2 = new Rectangle2D<C>[64];
            var queries3 = new Box<C>[64];
            for (int i = 0; i < 64; i++)
            {
                int x = random.Next(1000), y = random.Next(1000), z = random.Next(1000);
                int width = shape switch { "Point" => 0, "Small" => 20, "Broad" => 1000, _ => 2000 };
                if (shape == "All") x = y = z = -1;
                queries2[i] = new(N(x), N(y), N(x + width), N(y + width));
                queries3[i] = new(N(x), N(y), N(z), N(x + width), N(y + width), N(z + width));
            }
            // Validate complete multisets, independently of either traversal.
            for (int i = 0; i < 64; i++)
            {
                var expected2 = entries2.Where(e => e.Bounds.Intersects(queries2[i])).Select(e => e.Item).Order();
                var expected3 = entries3.Where(e => e.Bounds.Intersects(queries3[i])).Select(e => e.Item).Order();
                if (!after2.Search(queries2[i]).Order().SequenceEqual(expected2) || !before2.Search(queries2[i]).Order().SequenceEqual(expected2) ||
                    !after3.Search(queries3[i]).Order().SequenceEqual(expected3) || !before3.Search(queries3[i]).Order().SequenceEqual(expected3))
                    throw new InvalidOperationException("Generic linear oracle failed.");
                results.Clear(); after2Search(queries2[i], results);
                if (!results.Order().SequenceEqual(expected2)) throw new InvalidOperationException("Local 2D oracle failed.");
                results.Clear(); after3Search(queries3[i], results);
                if (!results.Order().SequenceEqual(expected3)) throw new InvalidOperationException("Local 3D oracle failed.");
            }
            Func<int> a2 = () => { int n = 0; foreach (var q in queries2) { results.Clear(); n += before2.Search(q, results); } return n; };
            Func<int> b2 = () => { int n = 0; foreach (var q in queries2) { results.Clear(); n += after2Search(q, results); } return n; };
            Func<int> a3 = () => { int n = 0; foreach (var q in queries3) { results.Clear(); n += before3.Search(q, results); } return n; };
            Func<int> b3 = () => { int n = 0; foreach (var q in queries3) { results.Clear(); n += after3Search(q, results); } return n; };
            foreach (var run in new[] { a2, b2, a3, b3 }) Screening.Measure(run, 200);
            for (int round = 0; round < 9; round++)
            foreach (int dimension in new[] { 2, 3 })
            foreach (bool before in round % 2 == 0 ? new[] { true, false } : new[] { false, true })
            {
                var sample = Screening.Measure(dimension == 2 ? (before ? a2 : b2) : (before ? a3 : b3), 60);
                writer.WriteLine(FormattableString.Invariant($"{typeof(C).Name}-{dimension}D-{shape},{(before ? "Before" : "After")},{round},{sample.Time},{sample.Allocation},{sample.Checksum}"));
                writer.Flush();
            }
            Console.WriteLine($"Generic screened {typeof(C).Name}/{shape}.");
        }
    }
}
