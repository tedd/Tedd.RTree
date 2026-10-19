using Tedd.RTree;

internal static class ProposalChecks
{
    internal static void Run()
    {
        foreach (int capacity in new[] { 4, 5, 8, 16, 17, 32, 128 })
        foreach (int n in new[] { 0, 1, 7, 127, 128, 129, 257, 1001, 2047, 2048, 4099 })
        {
            var random = new Random(9719 + n);
            var entries = Enumerable.Range(0, n).Select(i => {
                int x = random.Next(100), y = random.Next(100);
                return new SpatialEntry<int>(new(x, y, x + i % 11, y + i % 7), i % 31);
            }).ToArray();
            var original = entries.ToArray();
            var workspace = new BulkLoadWorkspace(n + 3);
            var tree = new PackedRTree<int>(new IndexedOnly(entries), capacity, workspace);
            Array.Clear(entries);
            _ = new PackedRTree<int>(original, capacity, workspace);
            for (int q = 0; q < 28; q++)
            {
                double x = random.Next(120) - 10, y = random.Next(120) - 10;
                double w = new[] { 0, 1, 20, 200 }[q % 4];
                Assert(tree, original, new(x, y, x + w, y + w));
            }
            var all = new Rectangle(-1, -1, 200, 200);
            var lists = new[] { new List<int>{-1}, new List<int>() }; int[] counts = new int[3];
            if (tree.SearchBatch([all, all], lists, counts) != 2L * n || counts[0] != n || counts[2] != 0 || lists[0][0] != -1)
                throw new Exception("Packed batch oracle mismatch");
            Assert(new PackedRTree<int>(original, capacity), original, all);
        }
        // Different input structure: long thin overlapping boxes, repeated keys and contacts.
        var thin = Enumerable.Range(0, 1003).Select(i => new SpatialEntry<int>(new(i % 17, -1000, i % 17, 1000), i)).ToArray();
        var packed = new PackedRTree<int>(thin);
        foreach (var q in new[] {new Rectangle(4,0,4,0),new Rectangle(-1,-2000,20,2000),new Rectangle(200,0,200,0)}) Assert(packed,thin,q);
        foreach (var box in new[] { new Rectangle(-double.MaxValue, -1, double.MaxValue, 1), new Rectangle(0, 0, double.Epsilon, double.Epsilon), new Rectangle(1, 1, 1, 1) })
        {
            var entries = Enumerable.Range(0, 1001).Select(i => new SpatialEntry<object>(box, new())).ToArray();
            IReadOnlySpatialIndex<Rectangle,object> tree = new PackedRTree<object>(entries);
            Parallel.For(0, 12, _ => { if (tree.Search(box).Count != entries.Length) throw new Exception("Immutable concurrent reads differ"); });
        }
        foreach (int capacity in new[]{3,129})
            try { _ = new PackedRTree<int>(Array.Empty<SpatialEntry<int>>(),capacity); throw new Exception("Invalid capacity accepted"); }
            catch (ArgumentOutOfRangeException) {}
        try { _ = new PackedRTree<int>(null!); throw new Exception("Null input accepted"); } catch (ArgumentNullException) {}
        var empty=new PackedRTree<int>(Array.Empty<SpatialEntry<int>>());
        try { empty.Search(default,null!); throw new Exception("Null output accepted"); } catch (ArgumentNullException) {}
        var untouched=new List<int>{42};
        try { empty.SearchBatch([default,default],[untouched,null!],new int[2]); throw new Exception("Null batch accepted"); } catch(ArgumentException) {}
        if(untouched.Count!=1)throw new Exception("Partial invalid batch output");
        try { empty.SearchBatch([default],Array.Empty<List<int>>(),new int[1]); throw new Exception("Bad lists length accepted"); } catch(ArgumentException) {}
        try { empty.SearchBatch([default],[untouched],Array.Empty<int>()); throw new Exception("Bad counts length accepted"); } catch(ArgumentException) {}
        ReadContracts();
        Console.WriteLine("Packed held-out geometry, thresholds, capacities, IDs, ownership, workspace, batch, concurrent-read and all nine interface contracts pass.");
    }

    private static void Assert(IReadOnlySpatialIndex<Rectangle,int> tree, SpatialEntry<int>[] entries, Rectangle query)
    {
        var result=new List<int>{-1};int found=tree.Search(query,result);
        if(tree.Count!=entries.Length || found!=result.Count-1 || result[0]!=-1 ||
            !result.Skip(1).Order().SequenceEqual(entries.Where(e=>e.Bounds.Intersects(query)).Select(e=>e.Item).Order()))
            throw new Exception("Packed independent oracle mismatch");
    }

    private static void ReadContracts()
    {
        using var c=new ConcurrentRTree<int>();
        using var c2=new ConcurrentRTree2D<int,int>();
        using var c3=new ConcurrentRTree3D<int,int>();
        IReadOnlySpatialIndex<Rectangle,int>[] original=[new RTree<int>(),new SnapshotRTree<int>(),c];
        IReadOnlySpatialIndex<Rectangle2D<int>,int>[] two=[new RTree2D<int,int>(),new SnapshotRTree2D<int,int>(),c2];
        IReadOnlySpatialIndex<Box<int>,int>[] three=[new RTree3D<int,int>(),new SnapshotRTree3D<int,int>(),c3];
        foreach(var tree in original) Empty(tree,default(Rectangle));
        foreach(var tree in two) Empty(tree,default(Rectangle2D<int>));
        foreach(var tree in three) Empty(tree,default(Box<int>));
        Write(new RTree<int>(),new Rectangle(0,0,1,1));
        Write(new RTree2D<int,int>(),new Rectangle2D<int>(0,0,1,1));
        Write(new RTree3D<int,int>(),new Box<int>(0,0,0,1,1,1));
        if((object)new PackedRTree<int>(Array.Empty<SpatialEntry<int>>()) is IMutableSpatialIndex<Rectangle,int>)
            throw new Exception("Immutable tree advertises mutation");
    }
    private static void Empty<B>(IReadOnlySpatialIndex<B,int> tree,B bounds) where B:struct
    {
        var list=new List<int>{42};int[] counts=[-1];
        if(tree.Count!=0 || tree.Search(bounds,list)!=0 || tree.Search(bounds).Count!=0 ||
            tree.SearchBatch([bounds],[list],counts)!=0 || counts[0]!=0 || list.Count!=1)
            throw new Exception("Read contract mismatch");
    }
    private static void Write<B>(IMutableSpatialIndex<B,int> tree,B bounds) where B:struct
    {
        tree.Insert(bounds,7);
        if(tree.Count!=1 || tree.Search(bounds).Single()!=7 || !tree.Update(bounds,7,bounds) || !tree.Remove(bounds,7))
            throw new Exception("Mutable contract mismatch");
        tree.Insert(bounds,8);tree.Clear();if(tree.Count!=0)throw new Exception("Clear contract mismatch");
    }
    private sealed class IndexedOnly(SpatialEntry<int>[] entries):IReadOnlyList<SpatialEntry<int>>
    {
        public int Count=>entries.Length;
        public SpatialEntry<int> this[int index]=>entries[index];
        public IEnumerator<SpatialEntry<int>> GetEnumerator()=>throw new Exception("Indexed input enumerated");
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator()=>GetEnumerator();
    }
}
