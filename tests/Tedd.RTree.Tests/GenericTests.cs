using System.Numerics;
using Tedd.RTree;

internal static class GenericTests
{
    private static void Check(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }

    internal static void Run()
    {
        RunFor<int>();
        RunFor<long>();
        RunFor<float>();
        RunFor<double>();
        CheckLargeLongs();

        foreach (float invalid in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity })
        {
            try { _ = new Rectangle2D<float>(invalid, 0, 1, 1); throw new Exception("Invalid float rectangle accepted."); }
            catch (ArgumentOutOfRangeException) { }
            try { _ = new Box<float>(invalid, 0, 0, 1, 1, 1); throw new Exception("Invalid float box accepted."); }
            catch (ArgumentOutOfRangeException) { }
        }
    }

    private static void RunFor<TCoordinate>() where TCoordinate : struct, INumber<TCoordinate>
    {
        static TCoordinate C(int value) => TCoordinate.CreateChecked(value);
        Random random = new(73211);
        SpatialEntry2D<TCoordinate, int>[] entries2D = new SpatialEntry2D<TCoordinate, int>[500];
        SpatialEntry3D<TCoordinate, int>[] entries3D = new SpatialEntry3D<TCoordinate, int>[500];
        for (int i = 0; i < entries2D.Length; i++)
        {
            int x = random.Next(-80, 80), y = random.Next(-80, 80), z = random.Next(-80, 80);
            entries2D[i] = new(new Rectangle2D<TCoordinate>(C(x), C(y), C(x + 1), C(y + 1)), i);
            entries3D[i] = new(new Box<TCoordinate>(C(x), C(y), C(z), C(x + 1), C(y + 1), C(z + 1)), i);
        }

        RTree2D<TCoordinate, int> inserted2D = new();
        RTree3D<TCoordinate, int> inserted3D = new();
        foreach (var entry in entries2D) inserted2D.Insert(entry.Bounds, entry.Item);
        foreach (var entry in entries3D) inserted3D.Insert(entry.Bounds, entry.Item);

        BulkLoadWorkspace workspace = new();
        RTree2D<TCoordinate, int> packed2D = new();
        RTree3D<TCoordinate, int> packed3D = new();
        packed2D.BulkLoad(entries2D, workspace);
        packed3D.BulkLoad(entries3D, workspace);

        for (int q = 0; q < 200; q++)
        {
            int x = random.Next(-85, 85), y = random.Next(-85, 85), z = random.Next(-85, 85);
            int width = q % 3 == 0 ? 0 : q % 3 == 1 ? 2 : 50;
            Rectangle2D<TCoordinate> query2D = new(C(x), C(y), C(x + width), C(y + width));
            Box<TCoordinate> query3D = new(C(x), C(y), C(z), C(x + width), C(y + width), C(z + width));
            int[] expected2D = entries2D.Where(e => e.Bounds.Intersects(query2D)).Select(e => e.Item).Order().ToArray();
            int[] expected3D = entries3D.Where(e => e.Bounds.Intersects(query3D)).Select(e => e.Item).Order().ToArray();
            Check(inserted2D.Search(query2D).Order().SequenceEqual(expected2D), $"2D insert query {typeof(TCoordinate)} {q}.");
            Check(packed2D.Search(query2D).Order().SequenceEqual(expected2D), $"2D packed query {typeof(TCoordinate)} {q}.");
            Check(inserted3D.Search(query3D).Order().SequenceEqual(expected3D), $"3D insert query {typeof(TCoordinate)} {q}.");
            Check(packed3D.Search(query3D).Order().SequenceEqual(expected3D), $"3D packed query {typeof(TCoordinate)} {q}.");
        }

        for (int i = 0; i < 100; i++)
        {
            var moved2D = new Rectangle2D<TCoordinate>(C(200 + i), C(200), C(201 + i), C(201));
            var moved3D = new Box<TCoordinate>(C(200 + i), C(200), C(200), C(201 + i), C(201), C(201));
            Check(packed2D.Update(entries2D[i].Bounds, i, moved2D), "2D packed update.");
            Check(packed3D.Update(entries3D[i].Bounds, i, moved3D), "3D packed update.");
            Check(packed2D.Search(moved2D).Contains(i), "2D updated entry missing.");
            Check(packed3D.Search(moved3D).Contains(i), "3D updated entry missing.");
            Check(packed2D.Remove(moved2D, i), "2D packed removal.");
            Check(packed3D.Remove(moved3D, i), "3D packed removal.");
        }

        SnapshotRTree2D<TCoordinate, int> snapshot2D = new();
        SnapshotRTree3D<TCoordinate, int> snapshot3D = new();
        snapshot2D.ReplaceAll(entries2D);
        snapshot3D.ReplaceAll(entries3D);
        Check(snapshot2D.Count == 500 && snapshot3D.Count == 500, "Generic snapshot count.");
        Check(snapshot2D.Search(entries2D[10].Bounds).Order().SequenceEqual(
                entries2D.Where(e => e.Bounds.Intersects(entries2D[10].Bounds)).Select(e => e.Item).Order()),
            "Generic 2D snapshot search.");
        Check(snapshot3D.Search(entries3D[10].Bounds).Order().SequenceEqual(
                entries3D.Where(e => e.Bounds.Intersects(entries3D[10].Bounds)).Select(e => e.Item).Order()),
            "Generic 3D snapshot search.");
        using ConcurrentRTree2D<TCoordinate, int> concurrent2D = new();
        using ConcurrentRTree3D<TCoordinate, int> concurrent3D = new();
        concurrent2D.BulkLoad(entries2D);
        concurrent3D.BulkLoad(entries3D);
        Check(concurrent2D.Move(0, entries2D[1].Bounds) && concurrent3D.Move(0, entries3D[1].Bounds), "Generic concurrent move.");
        Check(concurrent2D.Remove(0) && concurrent3D.Remove(0), "Generic concurrent remove.");
        Check(concurrent2D.Count == 499 && concurrent3D.Count == 499, "Generic concurrent count.");
        Check(!concurrent2D.Search(entries2D[0].Bounds).Contains(0) &&
              !concurrent3D.Search(entries3D[0].Bounds).Contains(0), "Generic concurrent removed entry visible.");
        snapshot2D.ReplaceAll([]);
        snapshot3D.ReplaceAll([]);
        Check(snapshot2D.Count == 0 && snapshot3D.Count == 0, "Generic snapshot replacement.");
    }

    private static void CheckLargeLongs()
    {
        long x = 9_007_199_254_740_993; // The first integer that double cannot represent exactly.
        Rectangle2D<long> first2D = new(x, x, x, x);
        Rectangle2D<long> next2D = new(x + 1, x, x + 1, x);
        Check(!first2D.Intersects(next2D), "Adjacent large long 2D points must remain distinct.");
        RTree2D<long, int> tree2D = new();
        tree2D.Insert(first2D, 1);
        tree2D.Insert(next2D, 2);
        Check(tree2D.Search(first2D).Single() == 1 && tree2D.Search(next2D).Single() == 2,
            "Large long 2D search precision.");
        Box<long> first = new(x, x, x, x, x, x);
        Box<long> next = new(x + 1, x, x, x + 1, x, x);
        Check(!first.Intersects(next), "Adjacent large long points must remain distinct.");
        RTree3D<long, int> tree = new();
        tree.Insert(first, 1);
        tree.Insert(next, 2);
        Check(tree.Search(first).Single() == 1 && tree.Search(next).Single() == 2, "Large long search precision.");
        RTree3D<long, int> packed = new();
        packed.BulkLoad(new[] { new SpatialEntry3D<long, int>(first, 1), new SpatialEntry3D<long, int>(next, 2) });
        Check(packed.Search(first).Single() == 1 && packed.Search(next).Single() == 2, "Large long packed precision.");

        var largeEntries = Enumerable.Range(0, 100)
            .Select(i => new SpatialEntry3D<long, int>(new Box<long>(x + i, 0, 0, x + i, 0, 0), i))
            .ToArray();
        RTree3D<long, int> largePacked = new();
        largePacked.BulkLoad(largeEntries);
        for (int i = 0; i < largeEntries.Length; i++)
            Check(largePacked.Search(largeEntries[i].Bounds).Single() == i,
                "Large long packed sorting or query precision.");

        Box<long> fullRange = new(long.MinValue, long.MinValue, long.MinValue,
            long.MaxValue, long.MaxValue, long.MaxValue);
        RTree3D<long, int> extreme = new(4);
        extreme.Insert(fullRange, 3);
        extreme.Insert(first, 1);
        for (int i = 0; i < 20; i++)
            extreme.Insert(new Box<long>(long.MinValue + i, 0, 0,
                long.MinValue + i, 0, 0), 100 + i);
        Check(extreme.Search(next).Single() == 3, "Extreme long volume or split overflow.");
    }
}
