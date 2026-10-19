using Tedd.RTree;
internal static class BoundaryChecks
{
    internal static void Run()
    {
        foreach(int capacity in new[]{4,5,8,16,17,32,128})
        foreach(int n in new[]{0,1,7,127,128,129,1001,2047,2048,4099})
        {
            var random=new Random(n+1837);
            var data=Enumerable.Range(0,n).Select(i=>{int x=random.Next(100),y=random.Next(100);return new SpatialEntry<int>(new(x,y,x+i%8,y+i%13),i%37);}).ToArray();
            var baseline=new PackedRTree<int>(data,capacity);
            var workspace=new BulkLoadWorkspace(n+3);
            var candidate=new BoundaryPackedRTree<int>(data,capacity,workspace);
            for(int q=0;q<25;q++)
            {
                int x=random.Next(120)-10,y=random.Next(120)-10,w=new[]{0,1,20,200}[q%4];var bounds=new Rectangle(x,y,x+w,y+w);
                var output=new List<int>{-1};int count=candidate.Search(bounds,output);
                var expected=data.Where(e=>e.Bounds.Intersects(bounds)).Select(e=>e.Item).Order();
                if(count!=output.Count-1||output[0]!=-1||!output.Skip(1).Order().SequenceEqual(expected)||!output.Skip(1).SequenceEqual(baseline.Search(bounds)))throw new Exception("Boundary oracle/order differs");
            }
        }
        Console.WriteLine("Inlining-boundary capacity, tail, exact-ID and output-order oracles pass.");
    }
}
