using System.Numerics;
using Tedd.RTree;

internal static class BatchTests
{
    private static void Check(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }

    internal static void Run()
    {
        CheckOriginal();
        CheckGeneric<int>();
        CheckGeneric<long>();
        CheckGeneric<float>();
        CheckGeneric<double>();
        CheckConcurrentVersions();
    }

    private static void CheckOriginal()
    {
        SpatialEntry<int>[] entries = [new(new(0, 0, 1, 1), 7), new(new(0, 0, 1, 1), 7), new(new(2, 2, 3, 3), 8)];
        Rectangle[] queries = [new(-1, -1, 4, 4), new(1, 1, 2, 2), new(20, 20, 30, 30), default];
        var tree = new RTree<int>(4);
        tree.BulkLoad(entries);
        using var concurrent = new ConcurrentRTree<int>(4);
        // The concurrent index requires unique keys; duplicates remain covered by the mutable/snapshot trees.
        concurrent.BulkLoad(entries.Where((_, i) => i != 1).ToArray());
        var snapshot = new SnapshotRTree<int>(4);
        snapshot.ReplaceAll(entries);
        List<int>[] outputs = queries.Select(_ => new List<int> { -1 }).ToArray();
        int[] counts = new int[queries.Length + 1];
        counts[^1] = 123;
        Check(tree.SearchBatch(queries, outputs, counts) == 8, "Batch total includes duplicates and boundary contact.");
        for (int i = 0; i < queries.Length; i++)
        {
            var expected = entries.Where(e => e.Bounds.Intersects(queries[i])).Select(e => e.Item).Order();
            Check(outputs[i][0] == -1 && outputs[i].Skip(1).Order().SequenceEqual(expected), "Batch linear oracle.");
            Check(counts[i] == outputs[i].Count - 1, "Batch appended count.");
            outputs[i].Clear();
        }
        Check(counts[^1] == 123, "Unused count slots are preserved.");
        Check(snapshot.SearchBatch(queries, outputs, counts) == 8, "Snapshot duplicate batch.");
        foreach (var output in outputs) output.Clear();
        Check(concurrent.SearchBatch(queries, outputs, counts) == 5, "Concurrent unique batch.");
        Check(tree.SearchBatch([], [], []) == 0, "Empty batch.");

        List<int>[] invalid = [new() { 99 }, null!];
        int[] unchanged = [91, 92];
        try { tree.SearchBatch(queries.AsSpan(0, 2), invalid, unchanged); throw new Exception("Accepted null result list."); }
        catch (ArgumentException) { }
        Check(invalid[0].SequenceEqual(new[] { 99 }) && unchanged.SequenceEqual(new[] { 91, 92 }), "Prevalidation is non-mutating.");
        try { tree.SearchBatch(queries, outputs.AsSpan(0, 1), counts); throw new Exception("Accepted mismatched lists."); }
        catch (ArgumentException) { }
        try { tree.SearchBatch(queries, outputs, counts.AsSpan(0, 1)); throw new Exception("Accepted short counts."); }
        catch (ArgumentException) { }

        tree.Remove(entries[0].Bounds, 7);
        tree.Update(entries[2].Bounds, 8, new(10, 10, 11, 11));
        foreach (var output in outputs) output.Clear();
        tree.SearchBatch(queries, outputs, counts);
        Check(counts[0] == 1 && counts[1] == 1 && counts[3] == 1, "Batch after removal and move.");
        tree.Clear();
        Check(tree.SearchBatch(queries, outputs, counts) == 0 && counts.Take(queries.Length).All(c => c == 0), "Batch empty tree.");
    }

    private static void CheckGeneric<C>() where C : struct, INumber<C>
    {
        static C N(int value) => C.CreateChecked(value);
        var rect = new Rectangle2D<C>(N(0), N(0), N(1), N(1));
        var box = new Box<C>(N(0), N(0), N(0), N(1), N(1), N(1));
        Rectangle2D<C>[] queries2 = [rect, new(N(1), N(1), N(2), N(2)), new(N(3), N(3), N(4), N(4))];
        Box<C>[] queries3 = [box, new(N(1), N(1), N(1), N(2), N(2), N(2)), new(N(3), N(3), N(3), N(4), N(4), N(4))];
        var tree2 = new RTree2D<C, int>();
        var tree3 = new RTree3D<C, int>();
        tree2.Insert(rect, 7);
        tree3.Insert(box, 7);
        using var concurrent2 = new ConcurrentRTree2D<C, int>();
        using var concurrent3 = new ConcurrentRTree3D<C, int>();
        concurrent2.Add(rect, 7);
        concurrent3.Add(box, 7);
        var snapshot2 = new SnapshotRTree2D<C, int>();
        var snapshot3 = new SnapshotRTree3D<C, int>();
        snapshot2.ReplaceAll([new(rect, 7)]);
        snapshot3.ReplaceAll([new(box, 7)]);
        List<int>[] results = [new(), new(), new()];
        int[] counts = new int[3];
        void Validate(long total)
        {
            Check(total == 2 && counts.SequenceEqual(new[] { 1, 1, 0 }), "Generic boundary batch counts.");
            Check(results[0].SequenceEqual(new[] { 7 }) && results[1].SequenceEqual(new[] { 7 }) && results[2].Count == 0, "Generic boundary batch values.");
            foreach (var result in results) result.Clear();
        }
        Validate(tree2.SearchBatch(queries2, results, counts));
        Validate(tree3.SearchBatch(queries3, results, counts));
        Validate(concurrent2.SearchBatch(queries2, results, counts));
        Validate(concurrent3.SearchBatch(queries3, results, counts));
        Validate(snapshot2.SearchBatch(queries2, results, counts));
        Validate(snapshot3.SearchBatch(queries3, results, counts));
    }

    private static void CheckConcurrentVersions()
    {
        Rectangle bounds = new(0, 0, 1, 1);
        Rectangle[] queries = Enumerable.Repeat(bounds, 128).ToArray();
        List<int>[] results = queries.Select(_ => new List<int>()).ToArray();
        int[] counts = new int[queries.Length];
        var snapshot = new SnapshotRTree<int>();
        SpatialEntry<int>[] a = [new(bounds, 7)], b = [new(bounds, 8)];
        snapshot.ReplaceAll(a);
        using var start = new ManualResetEventSlim(false);
        var writer = Task.Run(() => { start.Wait(); for (int i = 0; i < 2_000; i++) snapshot.ReplaceAll((i & 1) == 0 ? a : b); });
        start.Set();
        for (int i = 0; i < 2_000; i++)
        {
            foreach (var result in results) result.Clear();
            Check(snapshot.SearchBatch(queries, results, counts) == queries.Length, "Snapshot batch count.");
            Check(results.All(r => r.Count == 1 && r[0] == results[0][0]), "Batch crossed snapshot versions.");
        }
        writer.GetAwaiter().GetResult();

        using var concurrent = new ConcurrentRTree<int>();
        concurrent.Add(bounds, 7);
        var mover = Task.Run(() => { for (int i = 0; i < 2_000; i++) concurrent.Move(7, (i & 1) == 0 ? new(10, 10, 11, 11) : bounds); });
        for (int i = 0; i < 2_000; i++)
        {
            foreach (var result in results) result.Clear();
            concurrent.SearchBatch(queries, results, counts);
            Check(counts.All(c => c == counts[0]), "Batch crossed concurrent mutations.");
        }
        mover.GetAwaiter().GetResult();
        try { concurrent.SearchBatch(queries, [], counts); throw new Exception("Invalid concurrent batch accepted."); }
        catch (ArgumentException) { }
        Check(concurrent.Move(7, bounds), "Batch validation failed to release read lock.");
    }
}
