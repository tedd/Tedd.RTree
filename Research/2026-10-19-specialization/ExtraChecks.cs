using Tedd.RTree;

internal static class ExtraChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 16, 17, 128 })
        foreach (int n in new[] { 0, 1, 2, 3, 4, 7, 15, 16, 17, 127, 129, 257, 4099 })
        {
            var random = new Random(519 + n);
            var entries = Enumerable.Range(0, n).Select(i => { int x = random.Next(100), y = random.Next(100); return new SpatialEntry<int>(new(x, y, x + i % 11, y + i % 7), i % 31); }).ToArray();
            var workspace = new BulkLoadWorkspace(n + 3);
            IReadOnlySpatialIndex<Rectangle, int>[] trees =
            [new KeyPackedRTree<int>(entries, capacity, workspace: workspace),
             new ColumnPackedRTree<int>(entries, capacity, vectorWidth: 0),
             new ColumnPackedRTree<int>(entries, capacity, vectorWidth: 128),
             new ColumnPackedRTree<int>(entries, capacity, vectorWidth: 256)];
            foreach (var tree in trees)
            {
                for (int q = 0; q < 24; q++)
                {
                    double x = random.Next(120) - 10, y = random.Next(120) - 10, width = new[] { 0, 1, 20, 200 }[q % 4];
                    Rectangle query = new(x, y, x + width, y + width);
                    var output = new List<int> { -1 }; int found = tree.Search(query, output);
                    var expected = entries.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order();
                    if (found != output.Count - 1 || output[0] != -1 || !output.Skip(1).Order().SequenceEqual(expected)) throw new Exception("Column/key oracle mismatch");
                }
            }
        }
        foreach (var box in new[] { new Rectangle(-double.MaxValue, -1, double.MaxValue, 1), new Rectangle(0, 0, double.Epsilon, double.Epsilon), new Rectangle(-0.0, 0, 0, 0) })
        {
            var entries = Enumerable.Range(0, 1001).Select(i => new SpatialEntry<int>(box, i)).ToArray();
            IReadOnlySpatialIndex<Rectangle, int>[] trees = [new KeyPackedRTree<int>(entries), new ColumnPackedRTree<int>(entries)];
            foreach (var tree in trees)
                if (!tree.Search(box).Order().SequenceEqual(Enumerable.Range(0, entries.Length))) throw new Exception("Extreme key/column mismatch");
        }
        Console.WriteLine("Column scalar/128/256, key SIMD, tails, duplicate and extreme checks passed.");
    }
}
