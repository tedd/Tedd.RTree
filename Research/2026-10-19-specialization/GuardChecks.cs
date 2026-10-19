using Tedd.RTree;

internal static class GuardChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 16, 17, 128 })
        foreach (int n in new[] { 0, 1, 7, 16, 17, 127, 129, 1000, 2047, 2048, 4099 })
        {
            var random = new Random(n + 191044);
            var entries = Enumerable.Range(0, n).Select(i => { int x = random.Next(40), y = random.Next(40); return new SpatialEntry<int>(new(x, y, x + i % 5, y + i % 7), i); }).ToArray();
            var a = new PartitionRTree<int>(capacity); a.BulkLoad(entries);
            var b = new GuardPartitionRTree<int>(capacity); b.BulkLoad(entries);
            var c = new PackedRTree<int>(entries, capacity, partial: true);
            var d = new GuardPackedRTree<int>(entries, capacity, partial: true);
            var e = new LeafColumnPackedRTree<int>(entries, capacity, vectorWidth: 128);
            var f = new LeafColumnPackedRTree<int>(entries, capacity, vectorWidth: 256);
            for (int q = 0; q < 12; q++)
            {
                int x = random.Next(50), y = random.Next(50), width = random.Next(80);
                Rectangle query = new(x, y, x + width, y + width);
                var expected = entries.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order();
                var results = new[] { a.Search(query), b.Search(query), c.Search(query), d.Search(query), e.Search(query), f.Search(query) };
                if (results.Any(r => !r.Order().SequenceEqual(expected)) || !results[0].SequenceEqual(results[1]) || !results[2].SequenceEqual(results[3]))
                    throw new Exception("Guard changed partition membership or order");
            }
            for (int i = 0; i < Math.Min(n, 50); i++)
                if (!b.Update(entries[i].Bounds, i, new(-2, -2, -1, -1))) throw new Exception("Guard mutation failed");
        }
        Console.WriteLine("Guarded/unconditional partition exact membership and order checks passed.");
    }
}
