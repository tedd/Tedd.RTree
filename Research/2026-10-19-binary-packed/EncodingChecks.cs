using Tedd.RTree;

internal static class EncodingChecks
{
    internal static void Run()
    {
        var rng=new Random(39715);
        foreach(int n in new[]{1,3,4,5,7,8,9,15,16,17,127,128,129,2047,2048})
        foreach(int kind in Enumerable.Range(0,6))
        {
            var entries=Enumerable.Range(0,n).Select(i=>{
                double x,y;
                if(kind==0){x=rng.NextDouble()*1000-500;y=rng.NextDouble()*1000-500;}
                else if(kind==1){x=Math.ScaleB(rng.NextDouble()-.5,rng.Next(-1070,1024));y=Math.ScaleB(rng.NextDouble()-.5,rng.Next(-1070,1024));}
                else if(kind==2){x=i%3*double.Epsilon;y=i%5*double.Epsilon;}
                else if(kind==3){x=double.MaxValue;y=-double.MaxValue;}
                else if(kind==4){x=i%11;y=i%31;}
                else{x=-0.0;y=i;}
                double maxX=x,maxY=y;
                if(kind is 0 or 4){maxX+=rng.NextDouble()*20;maxY+=rng.NextDouble()*20;}
                return new SpatialEntry<int>(new(x,y,maxX,maxY),i);
            }).ToArray();
            Rectangle extent=entries[0].Bounds;
            for(int i=1;i<n;i++)extent=Rectangle.Union(extent,entries[i].Bounds);
            double minX=extent.MinX*.5,minY=extent.MinY*.5,width=extent.MaxX*.5-minX,height=extent.MaxY*.5-minY;
            double sx=width>0?65535/width:0,sy=height>0?65535/height:0;
            uint[] keys=new uint[n];int[] order=new int[n];
            KeyEncoding.Fill<int>(entries,keys,order,minX,minY,width,height,sx,sy);
            for(int i=0;i<n;i++)
            {
                var b=entries[i].Bounds;
                double x=b.MinX*.25+b.MaxX*.25-minX,y=b.MinY*.25+b.MaxY*.25-minY;
                uint ix=width>0?(uint)Math.Clamp(double.IsFinite(sx)?x*sx:x/width*65535,0,65535):0;
                uint iy=height>0?(uint)Math.Clamp(double.IsFinite(sy)?y*sy:y/height*65535,0,65535):0;
                if(order[i]!=i||keys[i]!=HilbertOrder.Encode(ix,iy))throw new Exception("Vector quantization key differs from scalar");
            }
            var originalKeys=keys.ToArray();var expected=keys.Order().ToArray();
            foreach(int capacity in new[]{4,5,16,17,128})
            {
                originalKeys.CopyTo(keys,0);for(int i=0;i<n;i++)order[i]=i;
                RefBinaryOrder.Sort(keys,order,capacity);
                for(int i=0;i<n;i+=capacity)
                    if(!keys.AsSpan(i,Math.Min(capacity,n-i)).ToArray().Order().SequenceEqual(expected.Skip(i).Take(capacity)))throw new Exception("Partial leaf partition differs");
                if(!order.Order().SequenceEqual(Enumerable.Range(0,n)))throw new Exception("Partial permutation lost item");
                for(int i=0;i<n;i++)if(keys[i]!=originalKeys[order[i]])throw new Exception("Partition key/payload alignment differs");
            }
        }
        Console.WriteLine("Exact vector/scalar key and partial-leaf partition oracles pass.");
    }
}
