using System.Numerics;
using Tedd.RTree;

internal static class LocalUpdateChecks
{
    internal static void Run()
    {
        Check<int>(); Check<long>(); Check<float>(); Check<double>();
        foreach (int capacity in new[] { 4, 5, 16, 128 })
        {
            var entries = Enumerable.Range(0, capacity).Select(i => new SpatialEntry<int>(new(i * 10, i * 10, i * 10 + 2, i * 10 + 2), i)).ToList();
            var tree = new RTree<int>(capacity); tree.BulkLoad(entries);
            for (int round = 0; round < 4; round++)
                for (int i = 0; i < entries.Count; i++)
                {
                    var old = entries[i]; double offset = round == 2 ? 10000 : round == 3 ? -10000 : 1;
                    var moved = new Rectangle(old.Bounds.MinX + offset, old.Bounds.MinY + offset, old.Bounds.MaxX + offset, old.Bounds.MaxY + offset);
                    if (!tree.Update(old.Bounds, i, moved) || tree.Update(old.Bounds, -1, moved)) throw new Exception("Original update match contract");
                    entries[i] = new(moved, i);
                    if (tree.Count != entries.Count) throw new Exception("Original update count");
                    foreach (var query in new[] { old.Bounds, moved, new Rectangle(-20000, -20000, 20000, 20000) })
                        if (!tree.Search(query).Order().SequenceEqual(entries.Where(e => e.Bounds.Intersects(query)).Select(e => e.Item).Order()))
                            throw new Exception("Original contained/far update results");
                }
        }
    }

    private static void Check<C>() where C : struct, INumber<C>
    {
        static C V(int n) => C.CreateChecked(n);
        static Rectangle2D<C> Rect(Box<C> b) => new(b.MinX, b.MinY, b.MaxX, b.MaxY);
        foreach (int capacity in new[] { 4, 5, 16, 128 })
        foreach (int count in new[] { 1, capacity, capacity * capacity + 3 })
        {
            var entries = Enumerable.Range(0, count).Select(i => new SpatialEntry3D<C, int>(
                new(V(i * 10), V(i * 10), V(i * 10), V(i * 10 + 2), V(i * 10 + 2), V(i * 10 + 2)), i)).ToList();
            // Matching duplicates must be moved one at a time, including no-op moves.
            entries.Add(entries[0]);
            var two = new RTree2D<C, int>(capacity); var three = new RTree3D<C, int>(capacity);
            two.BulkLoad(entries.Select(e => new SpatialEntry2D<C, int>(Rect(e.Bounds), e.Item)).ToArray()); three.BulkLoad(entries);
            for (int round = 0; round < 4; round++)
                for (int i = 0; i < Math.Min(entries.Count, 33); i++)
                {
                    var old = entries[i]; C delta = V(round == 0 ? 0 : round == 1 ? 1 : round == 2 ? 1000000 : -1000000);
                    var moved = new Box<C>(old.Bounds.MinX + delta, old.Bounds.MinY + delta, old.Bounds.MinZ + delta,
                        old.Bounds.MaxX + delta, old.Bounds.MaxY + delta, old.Bounds.MaxZ + delta);
                    if (!two.Update(Rect(old.Bounds), old.Item, Rect(moved)) || !three.Update(old.Bounds, old.Item, moved)) throw new Exception("Generic update match");
                    if (two.Update(Rect(old.Bounds), -1, Rect(moved)) || three.Update(old.Bounds, -1, moved)) throw new Exception("Generic missing update");
                    entries[i] = new(moved, old.Item);
                    if (two.Count != entries.Count || three.Count != entries.Count) throw new Exception("Generic update count");
                    foreach (var q in new[] { old.Bounds, moved })
                    {
                        if (!two.Search(Rect(q)).Order().SequenceEqual(entries.Where(e => Rect(e.Bounds).Intersects(Rect(q))).Select(e => e.Item).Order())) throw new Exception("2D local/far update oracle");
                        if (!three.Search(q).Order().SequenceEqual(entries.Where(e => e.Bounds.Intersects(q)).Select(e => e.Item).Order())) throw new Exception("3D local/far update oracle");
                    }
                }
            foreach (var e in entries)
                if (!two.Remove(Rect(e.Bounds), e.Item) || !three.Remove(e.Bounds, e.Item)) throw new Exception("Updated drain");
            if (two.Count != 0 || three.Count != 0) throw new Exception("Updated root collapse");
        }
    }
}
