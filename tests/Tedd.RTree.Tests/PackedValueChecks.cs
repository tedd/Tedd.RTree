using System.Runtime.CompilerServices;
using Tedd.RTree;

internal static class PackedValueChecks
{
    private sealed class Payload { }

    internal static void Run()
    {
        Check(CreateOriginal());
        Check(Create2D());
        Check(Create3D());
    }

    private static void Check((object Tree, WeakReference[] Removed) state)
    {
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();
        if (state.Removed.Any(value => value.IsAlive)) throw new Exception("Packed storage retained a removed value after condensation.");
        GC.KeepAlive(state.Tree);
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (object, WeakReference[]) CreateOriginal()
    {
        var entries = Enumerable.Range(0, 288)
            .Select(i => new SpatialEntry<Payload>(new Rectangle(i, i, i + 1, i + 1), new())).ToArray();
        var tree = new RTree<Payload>();
        tree.BulkLoad(entries);
        var ordered = tree.Search(new Rectangle(-1, -1, 400, 400));
        var removed = new[] { new WeakReference(ordered[256]), new WeakReference(ordered[272]) };
        // The last branch has two leaves. Removing from one condenses the branch
        // and reinserts the other, still-packed leaf. Then remove from that leaf.
        foreach (int index in new[] { 256, 272 })
        {
            var entry = entries.Single(entry => ReferenceEquals(entry.Item, ordered[index]));
            if (!tree.Remove(entry.Bounds, entry.Item)) throw new Exception("Packed removal failed.");
        }
        if (tree.Search(new Rectangle(-1, -1, 400, 400)).Count != 286)
            throw new Exception("Packed removal invalidation failed.");
        return (tree, removed);
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (object, WeakReference[]) Create2D()
    {
        var entries = Enumerable.Range(0, 288)
            .Select(i => new SpatialEntry2D<long, Payload>(new Rectangle2D<long>(i, i, i + 1, i + 1), new())).ToArray();
        var tree = new RTree2D<long, Payload>();
        tree.BulkLoad(entries);
        var ordered = tree.Search(new Rectangle2D<long>(-1, -1, 400, 400));
        var removed = new[] { new WeakReference(ordered[256]), new WeakReference(ordered[272]) };
        foreach (int index in new[] { 256, 272 })
        {
            var entry = entries.Single(entry => ReferenceEquals(entry.Item, ordered[index]));
            if (!tree.Remove(entry.Bounds, entry.Item)) throw new Exception("Packed 2D removal failed.");
        }
        if (tree.Search(new Rectangle2D<long>(-1, -1, 400, 400)).Count != 286)
            throw new Exception("Packed 2D removal invalidation failed.");
        return (tree, removed);
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (object, WeakReference[]) Create3D()
    {
        var entries = Enumerable.Range(0, 288)
            .Select(i => new SpatialEntry3D<int, Payload>(new Box<int>(i, i, i, i + 1, i + 1, i + 1), new())).ToArray();
        var tree = new RTree3D<int, Payload>();
        tree.BulkLoad(entries);
        var ordered = tree.Search(new Box<int>(-1, -1, -1, 400, 400, 400));
        var removed = new[] { new WeakReference(ordered[256]), new WeakReference(ordered[272]) };
        foreach (int index in new[] { 256, 272 })
        {
            var entry = entries.Single(entry => ReferenceEquals(entry.Item, ordered[index]));
            if (!tree.Remove(entry.Bounds, entry.Item)) throw new Exception("Packed 3D removal failed.");
        }
        if (tree.Search(new Box<int>(-1, -1, -1, 400, 400, 400)).Count != 286)
            throw new Exception("Packed 3D removal invalidation failed.");
        return (tree, removed);
    }
}
