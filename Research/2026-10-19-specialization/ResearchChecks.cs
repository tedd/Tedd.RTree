using Tedd.RTree;

internal static class ResearchChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 16, 17, 128 })
        foreach (int count in new[] { 0, 1, 3, 4, 7, 15, 16, 17, 63, 127, 129, 257, 2047, 2048, 4099 })
        {
            var random = new Random(count * 131 + capacity);
            var entries = Enumerable.Range(0, count).Select(i =>
            {
                double x = random.Next(100), y = random.Next(100);
                return new SpatialEntry<int>(new(x, y, x + random.Next(6), y + random.Next(6)), i % 37);
            }).ToArray();
            foreach (bool partial in new[] { false, true })
            {
                var workspace = new BulkLoadWorkspace(count + 11);
                var tree = new PackedRTree<int>(entries, capacity, partial, workspace);
                Assert(tree, entries, new Rectangle(-1, -1, 200, 200));
                for (int q = 0; q < 20; q++)
                {
                    double x = random.Next(110), y = random.Next(110), width = random.Next(50);
                    Assert(tree, entries, new Rectangle(x, y, x + width, y + width));
                }
                var query = new Rectangle(-1, -1, 200, 200);
                var lists = new[] { new List<int> { -1 }, new List<int>() }; var counts = new int[3];
                if (tree.SearchBatch([query, query], lists, counts) != 2L * count || lists[0][0] != -1 || counts[2] != 0)
                    throw new Exception("Batch contract differs");
                var originals = entries.ToArray();
                Array.Clear(entries);
                _ = new PackedRTree<int>(originals, capacity, !partial, workspace);
                Assert(tree, originals, query); // Neither input nor reused workspace is retained.
                originals.CopyTo(entries, 0);
                var indexed = new IndexedOnly(entries);
                Assert(new PackedRTree<int>(indexed, capacity, partial), entries, query);
            }
            var writer = new PartitionRTree<int>(capacity); writer.BulkLoad(entries);
            for (int i = 0; i < Math.Min(100, count); i++)
                if (!writer.Update(entries[i].Bounds, entries[i].Item, new(-20, -20, -10, -10))) throw new Exception("Partition update differs");
        }
        foreach (var box in new[] { new Rectangle(-double.MaxValue, -1, double.MaxValue, 1), new Rectangle(0, 0, double.Epsilon, double.Epsilon), new Rectangle(1, 1, 1, 1) })
        {
            var entries = Enumerable.Range(0, 4099).Select(i => new SpatialEntry<int>(box, i)).ToArray();
            foreach (bool partial in new[] { false, true }) Assert(new PackedRTree<int>(entries, partial: partial), entries, box);
        }
        var data = Enumerable.Range(0, 1001).Select(i => new SpatialEntry<object>(new(i, i, i + 1, i + 1), new())).ToArray();
        IReadOnlySpatialIndex<Rectangle, object> read = new PackedRTree<object>(data);
        if (read.Search(new(-1, -1, 2000, 2000)).Count != data.Length || read is IMutableSpatialIndex<Rectangle, object>)
            throw new Exception("Read-only interface contract differs");
        Parallel.For(0, 20, _ => { if (read.Search(new(-1, -1, 2000, 2000)).Count != data.Length) throw new Exception("Concurrent immutable reads differ"); });
        Console.WriteLine("Research capacity, tail, exact-ID, ownership, workspace, interface and concurrent-read checks passed.");
    }

    private static void Assert(IReadOnlySpatialIndex<Rectangle, int> tree, SpatialEntry<int>[] entries, Rectangle query)
    {
        var result = new List<int> { -1 }; int count = tree.Search(query, result);
        var expected = entries.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order();
        if (result[0] != -1 || count != result.Count - 1 || !result.Skip(1).Order().SequenceEqual(expected))
            throw new Exception("Independent packed oracle differs");
    }
    private sealed class IndexedOnly(SpatialEntry<int>[] entries) : IReadOnlyList<SpatialEntry<int>>
    {
        public int Count => entries.Length;
        public SpatialEntry<int> this[int index] => entries[index];
        public IEnumerator<SpatialEntry<int>> GetEnumerator() => throw new Exception("Enumeration is not part of indexed input contract");
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator() => GetEnumerator();
    }
}
