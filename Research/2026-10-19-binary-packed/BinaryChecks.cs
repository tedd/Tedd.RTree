using Tedd.RTree;

internal static class BinaryChecks
{
    internal static IReadOnlySpatialIndex<Rectangle, T> Build<T>(string mode, IReadOnlyList<SpatialEntry<T>> entries,
        int capacity = 16, BulkLoadWorkspace? workspace = null) => mode switch
    {
        "control" => new ControlPackedRTree<T>(entries, capacity, workspace),
        "binary" => new BinaryPackedRTree<T>(entries, capacity, workspace),
        "owned" => new OwnedPackedRTree<T>(entries, capacity, workspace),
        "split" => new SplitPackedRTree<T>(entries, capacity, workspace),
        "overlap" => new OverlapPackedRTree<T>(entries, capacity, workspace),
        "iterative" => new IterativePackedRTree<T>(entries, capacity, workspace),
        "ref" => new RefPackedRTree<T>(entries, capacity, workspace),
        "vector" => new VectorPackedRTree<T>(entries, capacity, workspace),
        "combined" => new CombinedPackedRTree<T>(entries, capacity, workspace),
        "stack" => new StackPackedRTree<T>(entries, capacity, workspace),
        "buffer" => new BufferPackedRTree<T>(entries, capacity, workspace),
        "stack-buffer" => new StackBufferPackedRTree<T>(entries, capacity, workspace),
        "predicate" => new PredicatePackedRTree<T>(entries, capacity, workspace),
        "predicate-buffer" => new PredicateBufferPackedRTree<T>(entries, capacity, workspace),
        "reduce" => new ReducePackedRTree<T>(entries, capacity, workspace),
        "wide" => new WidePackedRTree<T>(entries, capacity, workspace),
        "wide-reduce" => new WideReducePackedRTree<T>(entries, capacity, workspace),
        "normalized-scalar" => new NormalizedScalarPackedRTree<T>(entries, capacity, workspace),
        "normalized-vector" => new NormalizedVectorPackedRTree<T>(entries, capacity, workspace),
        _ => throw new ArgumentException(mode)
    };

    internal static string[] Modes = ["control", "binary", "owned", "split", "overlap", "iterative", "ref", "vector", "combined", "stack", "buffer", "stack-buffer", "predicate", "predicate-buffer", "reduce", "wide", "wide-reduce", "normalized-scalar", "normalized-vector"];

    internal static void Run()
    {
        EncodingChecks.Run();
        foreach (int capacity in new[] {4,5,8,16,17,32,127,128})
        foreach (int n in new[] {0,1,3,4,7,8,9,15,16,17,31,63,127,128,129,257,1001,2047,2048,4099})
        {
            var rng = new Random(90171 + n * 7 + capacity);
            var entries = Enumerable.Range(0,n).Select(i => {
                double x=rng.Next(100),y=rng.Next(100);
                return new SpatialEntry<int>(new(x,y,x+i%11,y+i%7),i%31);
            }).ToArray();
            var original=entries.ToArray();
            foreach (string mode in Modes)
            {
                var workspace=new BulkLoadWorkspace(n+11);
                var tree=Build(mode,new IndexedOnly<int>(entries),capacity,workspace);
                Array.Clear(entries);
                _=Build(mode,original,capacity,workspace);
                for(int q=0;q<24;q++)
                {
                    double x=rng.Next(120)-10,y=rng.Next(120)-10,w=new[]{0,1,20,200}[q%4];
                    Assert(tree,original,new(x,y,x+w,y+w));
                }
                Rectangle all=new(-1,-1,200,200);
                var lists=new[]{new List<int>{-1},new List<int>()};var counts=new int[3];
                if(tree.SearchBatch([all,all],lists,counts)!=2L*n||counts[0]!=n||counts[1]!=n||counts[2]!=0||lists[0][0]!=-1)
                    throw new Exception("Batch counts/appending differ");
                Assert(Build(mode,original,capacity),original,all);
                original.CopyTo(entries,0);
            }
        }
        foreach(string mode in Modes)
        {
            foreach(Rectangle box in new[]{new Rectangle(-double.MaxValue,-1,double.MaxValue,1),new Rectangle(0,0,double.Epsilon,double.Epsilon),new Rectangle(1,1,1,1)})
            {
                var entries=Enumerable.Range(0,1003).Select(i=>new SpatialEntry<int>(box,i)).ToArray();
                Assert(Build(mode,entries),entries,box);
                Assert(Build(mode,entries),entries,new(-1,-1,1,1));
            }
            // Mixed signs/extremes, small exponents and repeated centers produce common prefixes and ties.
            var rng=new Random(7731);
            var mixed=Enumerable.Range(0,1003).Select(i=>{
                double x=Math.ScaleB((rng.NextDouble()-.5),rng.Next(-1070,1024));
                double y=Math.ScaleB((rng.NextDouble()-.5),rng.Next(-1070,1024));
                return new SpatialEntry<int>(new(x,y,x,y),i);
            }).ToArray();
            var tree=Build(mode,mixed);
            foreach(var entry in mixed.Where((_,i)=>i%11==0))Assert(tree,mixed,entry.Bounds);
            var thin=Enumerable.Range(0,1003).Select(i=>new SpatialEntry<int>(new(i%17,-1000,i%17,1000),i)).ToArray();
            foreach(Rectangle query in new[]{new Rectangle(4,0,4,0),new Rectangle(-1,-2000,20,2000),new Rectangle(200,0,200,0)})
                Assert(Build(mode,thin),thin,query);
            var noHitOutput=new List<int>{-1};var enumerator=noHitOutput.GetEnumerator();enumerator.MoveNext();
            if(Build(mode,thin).Search(new(4.5,0,4.5,0),noHitOutput)!=0||enumerator.MoveNext())
                throw new Exception("No-hit append/version contract differs");
            // Reference payloads must remain valid through moving GC and arbitrary owned swaps.
            var objects=Enumerable.Range(0,1003).Select(i=>new SpatialEntry<Payload>(new(i%17,i%31,i%17+1,i%31+1),new(i))).ToArray();
            var referenceTree=Build(mode,objects);
            GC.Collect(2,GCCollectionMode.Forced,true,true);
            var ids=referenceTree.Search(new(-1,-1,2000,2000)).Select(p=>p.Id).Order();
            if(!ids.SequenceEqual(Enumerable.Range(0,objects.Length)))throw new Exception("Reference ownership differs");
            Parallel.For(0,12,_=>{if(referenceTree.Search(new(-1,-1,2000,2000)).Count!=objects.Length)throw new Exception("Concurrent read differs");});
            foreach(int capacity in new[]{3,129})
                Throws<ArgumentOutOfRangeException>(()=>Build(mode,Array.Empty<SpatialEntry<int>>(),capacity));
            Throws<ArgumentNullException>(()=>Build<int>(mode,null!));
            var empty=Build(mode,Array.Empty<SpatialEntry<int>>());
            Throws<ArgumentNullException>(()=>empty.Search(default,null!));
            var untouched=new List<int>{42};
            Throws<ArgumentException>(()=>empty.SearchBatch([default,default],[untouched,null!],new int[2]));
            if(untouched.Count!=1)throw new Exception("Invalid batch partially appended");
            Throws<ArgumentException>(()=>empty.SearchBatch([default],[],new int[1]));
            Throws<ArgumentException>(()=>empty.SearchBatch([default],[untouched],[]));
        }
        Console.WriteLine("Binary variants: exact IDs, boundaries, duplicates, numerical extremes, ownership, workspace reuse, indexed input, batch, GC and concurrent-read oracles pass.");
    }

    private static void Assert(IReadOnlySpatialIndex<Rectangle,int> tree,SpatialEntry<int>[] entries,Rectangle query)
    {
        List<int> result=[-1];int found=tree.Search(query,result);
        if(tree.Count!=entries.Length||found!=result.Count-1||result[0]!=-1||!result.Skip(1).Order().SequenceEqual(entries.Where(e=>e.Bounds.Intersects(query)).Select(e=>e.Item).Order()))
            throw new Exception("Independent exact-ID oracle differs");
    }
    private static void Throws<T>(Action action) where T:Exception
    {
        try{action();}catch(T){return;}throw new Exception("Expected exception absent: "+typeof(T).Name);
    }
    private sealed record Payload(int Id);
    private sealed class IndexedOnly<T>(SpatialEntry<T>[] entries):IReadOnlyList<SpatialEntry<T>>
    {
        public int Count=>entries.Length;
        public SpatialEntry<T> this[int i]=>entries[i];
        public IEnumerator<SpatialEntry<T>> GetEnumerator()=>throw new Exception("Indexed input enumerated");
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator()=>GetEnumerator();
    }
}
