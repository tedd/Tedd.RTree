using Tedd.RTree;

internal static class Construction
{
    internal static void Run(string output)
    {
        using StreamWriter writer = new(output);
        writer.WriteLine("Scenario,Variant,Round,Microseconds,AllocatedBytes,Checksum");
        foreach (bool clustered in new[] { false, true })
        foreach (int size in new[] { 1_000, 10_000 })
        {
            var f = new Fixture("Medium", clustered, size);
            List<(string Name, Func<int> Run)> variants =
            [
                ("Quadratic", () => { var tree = new BaselineRTree<int>(); foreach (var e in f.Entries) tree.Insert(e.Bounds, e.Item); return tree.Count; }),
                ("CachedAreas", () => { var tree = new CachedAreasRTree<int>(); foreach (var e in f.Entries) tree.Insert(e.Bounds, e.Item); return tree.Count; }),
                ("StackAssigned", () => { var tree = new StackAssignedRTree<int>(); foreach (var e in f.Entries) tree.Insert(e.Bounds, e.Item); return tree.Count; }),
                ("LinearSplit", () => { var tree = new LinearSplitRTree<int>(); foreach (var e in f.Entries) tree.Insert(e.Bounds, e.Item); return tree.Count; }),
                ("STR", () => { var tree = new BaselineRTree<int>(); tree.BulkLoad(f.Entries); return tree.Count; })
            ];
            var cache = new CachedAreasRTree<int>();
            var stack = new StackAssignedRTree<int>();
            var linear = new LinearSplitRTree<int>();
            var reference = new BaselineRTree<int>();
            foreach (var e in f.Entries)
            {
                cache.Insert(e.Bounds, e.Item); stack.Insert(e.Bounds, e.Item);
                linear.Insert(e.Bounds, e.Item); reference.Insert(e.Bounds, e.Item);
            }
            f.Validate(cache.Search); f.Validate(stack.Search); f.Validate(linear.Search); f.Validate(reference.Search);
            variants.Add(("QuadraticQuery", () => f.Query(reference.Search)));
            variants.Add(("LinearQuery", () => f.Query(linear.Search)));
            foreach (var variant in variants) Screening.Measure(variant.Run, 150);
            for (int round = 0; round < 9; round++)
            foreach (var variant in round % 2 == 0 ? variants : variants.AsEnumerable().Reverse())
            {
                var sample = Screening.Measure(variant.Run, 60);
                writer.WriteLine(FormattableString.Invariant($"{(clustered ? "Clustered" : "Uniform")}-{size},{variant.Name},{round},{sample.Time},{sample.Allocation},{sample.Checksum}"));
                writer.Flush();
            }
            Console.WriteLine($"Construction screened {clustered}/{size}.");
        }
    }
}
