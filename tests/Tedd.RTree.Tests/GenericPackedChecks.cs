using System.Collections;
using System.Numerics;
using Tedd.RTree;

internal static class GenericPackedChecks
{
    internal static void Run()
    {
        var workspace = new BulkLoadWorkspace();
        RunFor<int>(workspace); RunFor<long>(workspace); RunFor<float>(workspace); RunFor<double>(workspace);
        CheckEdges<long>(workspace, new[] { long.MinValue, long.MinValue + 1, -1L, 0L, 9_007_199_254_740_993L, long.MaxValue - 1, long.MaxValue });
        CheckEdges<int>(workspace, new[] { int.MinValue, int.MinValue + 1, -1, 0, 1, int.MaxValue - 1, int.MaxValue });
        foreach (double unit in new[] { double.Epsilon, 1e-310, 1e-200, 1e200 })
            CheckEdges<double>(workspace, Enumerable.Range(-16,33).Select(i => i * unit).ToArray());
        CheckEdges<double>(workspace, new[] { -double.MaxValue, -1.0, -0.0, double.Epsilon, 1.0, double.MaxValue });
        CheckEdges<float>(workspace, new[] { -float.MaxValue, -1f, -0f, float.Epsilon, 1f, float.MaxValue });
        long origin = 9_007_199_254_740_993L;
        var zEntries = Enumerable.Range(0,4097).Select(i => new SpatialEntry3D<long,int>(
            new Box<long>(0,0,origin+i,0,0,origin+i),i)).ToArray();
        var zTree = new RTree3D<long,int>(); zTree.BulkLoad(zEntries,workspace);
        for(int i=0;i<zEntries.Length;i+=17)
            if(!zTree.Search(zEntries[i].Bounds).SequenceEqual(new[]{i}))throw new Exception("3D z-only large-integer precision");
        CheckSnapshotPublication();
    }

    private static void RunFor<C>(BulkLoadWorkspace workspace) where C : struct, INumber<C>
    {
        static C V(int x) => C.CreateChecked(x);
        foreach (int capacity in new[] { 4,5,16,128 })
        {
            var random = new Random(81929 + capacity);
            var expected = new List<SpatialEntry3D<C,string>>();
            for (int i = 0; i < capacity * capacity + 17; i++)
            {
                int x=random.Next(-500,500),y=random.Next(-500,500),z=random.Next(-500,500);
                expected.Add(new(new Box<C>(V(x),V(y),V(z),V(x+random.Next(10)),V(y+random.Next(10)),V(z+random.Next(10))),$"v{i}"));
            }
            expected.Add(expected[0]);
            var source3=expected.ToArray();
            var source2=source3.Select(e=>new SpatialEntry2D<C,string>(Rect(e.Bounds),e.Item)).ToArray();
            var two=new RTree2D<C,string>(capacity);var three=new RTree3D<C,string>(capacity);
            two.BulkLoad(new IndexedOnly<SpatialEntry2D<C,string>>(source2),workspace);
            three.BulkLoad(new IndexedOnly<SpatialEntry3D<C,string>>(source3),workspace);
            if(!source3.SequenceEqual(expected))throw new Exception("Generic input changed");
            Verify(two,three,expected,new(V(-1000),V(-1000),V(-1000),V(1000),V(1000),V(1000)));
            for(int step=0;step<160;step++)
            {
                int selected=random.Next(expected.Count);var old=expected[selected];
                var bounds=new Box<C>(V(step-300),V(-step),V(step),V(step-298),V(-step+2),V(step+2));
                if(step%3==0)
                {
                    if(!two.Remove(Rect(old.Bounds),old.Item)||!three.Remove(old.Bounds,old.Item))throw new Exception("Generic packed removal");
                    expected.RemoveAt(selected);
                }
                else if(step%3==1)
                {
                    if(!two.Update(Rect(old.Bounds),old.Item,Rect(bounds))||!three.Update(old.Bounds,old.Item,bounds))throw new Exception("Generic packed move");
                    expected[selected]=new(bounds,old.Item);
                }
                else
                {
                    two.Insert(Rect(bounds),$"new{step}");three.Insert(bounds,$"new{step}");expected.Add(new(bounds,$"new{step}"));
                }
                Verify(two,three,expected,bounds);
                int x=random.Next(-700,700),y=random.Next(-700,700),z=random.Next(-700,700);
                Verify(two,three,expected,new(V(x),V(y),V(z),V(x+250),V(y+250),V(z+250)));
            }
            foreach(var entry in expected)
                if(!two.Remove(Rect(entry.Bounds),entry.Item)||!three.Remove(entry.Bounds,entry.Item))throw new Exception("Generic packed drain/root collapse");
            if(two.Count!=0||three.Count!=0)throw new Exception("Generic packed empty count");
            two.BulkLoad(source2,workspace);three.BulkLoad(source3,workspace);
            Verify(two,three,source3,new(V(-1000),V(-1000),V(-1000),V(1000),V(1000),V(1000)));
            var original=new RTree<int>();original.BulkLoad(Enumerable.Range(0,4097).Select(i=>new SpatialEntry<int>(new Rectangle(i,i,i+1,i+1),i)).ToArray(),workspace);
            if(original.Search(new Rectangle(-1,-1,5000,5000)).Count!=4097)throw new Exception("Cross-API workspace reuse");
        }
    }

    private static void CheckEdges<C>(BulkLoadWorkspace workspace,C[] coordinates) where C : struct,INumber<C>
    {
        foreach(int count in new[]{0,1,4,5,17,257,4097})
        {
            var entries=Enumerable.Range(0,count).Select(i=>{C p=coordinates[i%coordinates.Length];return new SpatialEntry3D<C,string>(new(p,p,p,p,p,p),$"edge{i}");}).ToArray();
            var two=new RTree2D<C,string>(4);var three=new RTree3D<C,string>(4);
            two.BulkLoad(entries.Select(e=>new SpatialEntry2D<C,string>(Rect(e.Bounds),e.Item)).ToArray(),workspace);three.BulkLoad(entries,workspace);
            foreach(C p in coordinates)Verify(two,three,entries,new(p,p,p,p,p,p));
        }
    }

    private static Rectangle2D<C> Rect<C>(Box<C> b) where C:struct,INumber<C> => new(b.MinX,b.MinY,b.MaxX,b.MaxY);
    private static void CheckSnapshotPublication()
    {
        var a=Enumerable.Range(0,257).Select(i=>new SpatialEntry3D<int,int>(new Box<int>(i,i,i,i+1,i+1,i+1),i)).ToArray();
        var b=a.Select(e=>new SpatialEntry3D<int,int>(e.Bounds,e.Item+10000)).ToArray();
        var snapshot=new SnapshotRTree3D<int,int>();snapshot.ReplaceAll(a);
        var query=new Box<int>(-1,-1,-1,1000,1000,1000);
        var writer=Task.Run(()=>{for(int i=0;i<100;i++)snapshot.ReplaceAll((i&1)==0?b:a);});
        var readers=Enumerable.Range(0,3).Select(_=>Task.Run(()=>
        {
            for(int i=0;i<150;i++)
            {
                var found=snapshot.Search(query);found.Sort();
                if(!found.SequenceEqual(Enumerable.Range(0,257))&&!found.SequenceEqual(Enumerable.Range(10000,257)))throw new Exception("3D snapshot exposed partial publication");
            }
        })).ToArray();
        Task.WaitAll(readers.Append(writer).ToArray());
    }
    private static void Verify<C>(RTree2D<C,string> two,RTree3D<C,string> three,IReadOnlyList<SpatialEntry3D<C,string>> entries,Box<C> query) where C:struct,INumber<C>
    {
        var rect=Rect(query);var a=new List<string>{"prefix"};var b=new List<string>{"prefix"};
        int n2=two.Search(rect,a),n3=three.Search(query,b);
        // Oracle compares coordinates directly, independently of index predicates/packing keys.
        var expected2=entries.Where(e=>e.Bounds.MinX<=rect.MaxX&&e.Bounds.MaxX>=rect.MinX&&e.Bounds.MinY<=rect.MaxY&&e.Bounds.MaxY>=rect.MinY).Select(e=>e.Item).Order();
        var expected3=entries.Where(e=>e.Bounds.MinX<=query.MaxX&&e.Bounds.MaxX>=query.MinX&&e.Bounds.MinY<=query.MaxY&&e.Bounds.MaxY>=query.MinY&&e.Bounds.MinZ<=query.MaxZ&&e.Bounds.MaxZ>=query.MinZ).Select(e=>e.Item).Order();
        if(two.Count!=entries.Count||three.Count!=entries.Count||a[0]!="prefix"||b[0]!="prefix"||n2!=a.Count-1||n3!=b.Count-1||!a.Skip(1).Order().SequenceEqual(expected2)||!b.Skip(1).Order().SequenceEqual(expected3))throw new Exception("Generic packed differential/append failure");
    }
    private sealed class IndexedOnly<E>(E[] entries):IReadOnlyList<E>
    {
        public int Count=>entries.Length;public E this[int i]=>entries[i];
        public IEnumerator<E> GetEnumerator()=>throw new Exception("Indexed input contract");IEnumerator IEnumerable.GetEnumerator()=>GetEnumerator();
    }
}
