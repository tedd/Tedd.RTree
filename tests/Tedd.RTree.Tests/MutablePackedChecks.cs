using Tedd.RTree;

internal static class MutablePackedChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 16, 128 })
        {
            var random = new Random(81119 + capacity);
            var expected = new List<SpatialEntry<string>>();
            for (int i = 0; i < capacity * capacity + 17; i++)
            {
                double x = random.Next(-500, 500), y = random.Next(-500, 500);
                expected.Add(new(new Rectangle(x, y, x + random.Next(10), y + random.Next(10)), $"item-{i}"));
            }
            expected.Add(expected[0]); // Duplicate value and bounds must remain independent entries.
            var source = expected.ToArray();
            var tree = new RTree<string>(capacity);
            var workspace = new BulkLoadWorkspace();
            tree.BulkLoad(source, workspace);
            if (!source.SequenceEqual(expected)) throw new Exception("Bulk load changed source order.");
            Check(tree, expected, new Rectangle(-1000, -1000, 1000, 1000));
            for (int step = 0; step < 600; step++)
            {
                int selected = random.Next(expected.Count);
                var old = expected[selected];
                var b = new Rectangle(step - 300, -step, step - 298, -step + 2);
                if (step % 3 == 0)
                {
                    if (!tree.Remove(old.Bounds, old.Item)) throw new Exception("Bulk-built remove failed.");
                    expected.RemoveAt(selected);
                }
                else if (step % 3 == 1)
                {
                    if (!tree.Update(old.Bounds, old.Item, b)) throw new Exception("Bulk-built update failed.");
                    expected[selected] = new(b, old.Item);
                }
                else
                {
                    var added = new SpatialEntry<string>(b, $"new-{step}");
                    tree.Insert(b, added.Item);
                    expected.Add(added);
                }
                if (tree.Count != expected.Count) throw new Exception("Mutable packed count mismatch.");
                Check(tree, expected, b);
                double x = random.Next(-700, 700), y = random.Next(-700, 700);
                Check(tree, expected, new Rectangle(x, y, x + random.Next(400), y + random.Next(400)));
            }
            foreach (var entry in expected.ToArray())
                if (!tree.Remove(entry.Bounds, entry.Item)) throw new Exception("Packed condense/root collapse failed.");
            if (tree.Count != 0) throw new Exception("Packed tree failed to empty.");
            tree.BulkLoad(source, workspace);
            Check(tree, source, new Rectangle(-1000, -1000, 1000, 1000));
        }
        var edge = new[]
        {
            new Rectangle(-double.MaxValue, -double.MaxValue, double.MaxValue, double.MaxValue),
            new Rectangle(double.MaxValue, double.MaxValue, double.MaxValue, double.MaxValue),
            new Rectangle(-double.MaxValue, -double.MaxValue, -double.MaxValue, -double.MaxValue),
            new Rectangle(-double.Epsilon, -double.Epsilon, double.Epsilon, double.Epsilon),
            new Rectangle(0, -0.0, 0, -0.0)
        };
        foreach (int count in new[] { 0, 1, 4, 5, 17, 257 })
        {
            var entries = Enumerable.Range(0, count).Select(i => new SpatialEntry<string>(edge[i % edge.Length], $"e{i}")).ToArray();
            var tree = new RTree<string>(4);
            tree.BulkLoad(entries);
            foreach (var q in edge) Check(tree, entries, q);
            var indexed = new RTree<string>(4);
            indexed.BulkLoad(new IndexedOnly(entries));
            foreach (var q in edge) Check(indexed, entries, q);
        }
        var shared = new BulkLoadWorkspace();
        for (int pass = 0; pass < 4; pass++)
        {
            var batch = Enumerable.Range(0, 4097).Select(i => new SpatialEntry<int>(new Rectangle(i % 997, i % 997, i % 997 + 1, i % 997 + 1), i)).ToArray();
            var original = new RTree<int>(); original.BulkLoad(batch, shared);
            if (original.Search(new Rectangle(-1, -1, 1000, 1000)).Count != batch.Length) throw new Exception("Shared workspace original failure.");
            var generic = new RTree2D<double, int>();
            generic.BulkLoad(batch.Select(e => new SpatialEntry2D<double, int>(new Rectangle2D<double>(e.Bounds.MinX, e.Bounds.MinY, e.Bounds.MaxX, e.Bounds.MaxY), e.Item)).ToArray(), shared);
            if (generic.Search(new Rectangle2D<double>(-1, -1, 1000, 1000)).Count != batch.Length) throw new Exception("Shared workspace generic failure.");
        }
    }

    private static void Check(RTree<string> tree, IReadOnlyList<SpatialEntry<string>> entries, Rectangle q)
    {
        var expected = entries.Where(e => e.Bounds.MinX <= q.MaxX && e.Bounds.MaxX >= q.MinX &&
            e.Bounds.MinY <= q.MaxY && e.Bounds.MaxY >= q.MinY).Select(e => e.Item).Order().ToArray();
        var actual = new List<string> { "prefix" };
        int found = tree.Search(q, actual);
        if (actual[0] != "prefix" || found != expected.Length || !actual.Skip(1).Order().SequenceEqual(expected))
            throw new Exception("Mutable packed differential/append failure.");
    }

    private sealed class IndexedOnly(SpatialEntry<string>[] items) : IReadOnlyList<SpatialEntry<string>>
    {
        public int Count => items.Length;
        public SpatialEntry<string> this[int index] => items[index];
        public IEnumerator<SpatialEntry<string>> GetEnumerator() => throw new Exception("Bulk load must use the indexed contract.");
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator() => GetEnumerator();
    }
}
