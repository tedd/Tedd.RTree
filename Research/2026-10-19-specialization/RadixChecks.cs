using Tedd.RTree;

internal static class RadixChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 8, 16, 17, 32, 128 })
        foreach (int n in new[] { 0, 1, 7, 127, 128, 129, 257, 1001, 2047, 2048, 4099 })
        {
            var random = new Random(719 + n);
            var entries = Enumerable.Range(0, n).Select(i => {
                int x = random.Next(100), y = random.Next(100);
                return new SpatialEntry<int>(new(x, y, x + i % 11, y + i % 7), i % 31);
            }).ToArray();
            var workspace = new BulkLoadWorkspace(n + 3);
            var tree = new RadixPackedRTree<int>(entries, capacity, workspace: workspace);
            var original = entries.ToArray();
            Array.Clear(entries);
            _ = new RadixPackedRTree<int>(original, capacity, workspace: workspace);
            for (int q = 0; q < 28; q++)
            {
                double x = random.Next(120) - 10, y = random.Next(120) - 10;
                double w = new[] { 0, 1, 20, 200 }[q % 4];
                Rectangle query = new(x, y, x + w, y + w);
                var output = new List<int> { -1 }; int found = tree.Search(query, output);
                var expected = original.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order();
                if (found != output.Count - 1 || output[0] != -1 || !output.Skip(1).Order().SequenceEqual(expected))
                    throw new Exception("Small-radix exact/ownership oracle mismatch");
            }
            var all = new Rectangle(-1, -1, 200, 200);
            var lists = new[] { new List<int>{-1}, new List<int>() }; int[] counts = new int[3];
            if (tree.SearchBatch([all, all], lists, counts) != 2L * n || counts[0] != n || counts[2] != 0 || lists[0][0] != -1)
                throw new Exception("Small-radix batch oracle mismatch");
        }
        foreach (var box in new[] { new Rectangle(-double.MaxValue, -1, double.MaxValue, 1), new Rectangle(0, 0, double.Epsilon, double.Epsilon), new Rectangle(1, 1, 1, 1) })
        {
            var entries = Enumerable.Range(0, 1001).Select(i => new SpatialEntry<object>(box, new())).ToArray();
            var tree = new RadixPackedRTree<object>(entries);
            Parallel.For(0, 12, _ => { if (tree.Search(box).Count != entries.Length) throw new Exception("Immutable concurrent reads differ"); });
        }
        Console.WriteLine("Small-radix thresholds, capacities, exact IDs, ownership, workspace, batch and concurrent reads pass.");
    }
}
