using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Intrinsics;
using System.Runtime.Intrinsics.X86;

namespace Tedd.RTree;

// Inputs are owned/exclusively leased spans of equal length. Vector loops only access
// complete four/eight-entry blocks; scalar tails preserve the public numeric contract.
internal static class PackedKeyEncoding
{
    internal static void Fill<T>(ReadOnlySpan<SpatialEntry<T>> source, Span<uint> keys, Span<int> order,
        double minX, double minY, double width, double height, double scaleX, double scaleY)
    {
        int i = 0;
        bool finiteX = double.IsFinite(scaleX), finiteY = double.IsFinite(scaleY);
        if (Avx.IsSupported && width > 0 && height > 0 && finiteX && finiteY)
        {
            var quarter = Vector256.Create(0.25);
            var originX = Vector256.Create(minX); var originY = Vector256.Create(minY);
            var sx = Vector256.Create(scaleX); var sy = Vector256.Create(scaleY);
            var zero = Vector256<double>.Zero; var maximum = Vector256.Create(65535.0);
            int end = source.Length & ~3;
            for (; i < end; i += 4)
            {
                Rectangle a = source[i].Bounds, b = source[i+1].Bounds, c = source[i+2].Bounds, d = source[i+3].Bounds;
                var va = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref a));
                var vb = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref b));
                var vc = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref c));
                var vd = Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref d));
                var xab = Avx.UnpackLow(va,vb); var xcd = Avx.UnpackLow(vc,vd);
                var yab = Avx.UnpackHigh(va,vb); var ycd = Avx.UnpackHigh(vc,vd);
                var x0 = Avx.Permute2x128(xab,xcd,0x20); var x1 = Avx.Permute2x128(xab,xcd,0x31);
                var y0 = Avx.Permute2x128(yab,ycd,0x20); var y1 = Avx.Permute2x128(yab,ycd,0x31);
                // Preserve the scalar operation order, including overflow-safe quarter centers.
                var x = ((x0 * quarter + x1 * quarter) - originX) * sx;
                var y = ((y0 * quarter + y1 * quarter) - originY) * sy;
                x = Avx.Min(Avx.Max(x,zero),maximum); y = Avx.Min(Avx.Max(y,zero),maximum);
                var ix = Avx.ConvertToVector128Int32WithTruncation(x).AsUInt32();
                var iy = Avx.ConvertToVector128Int32WithTruncation(y).AsUInt32();
                var packed = ix | (iy << 16);
                packed.StoreUnsafe(ref MemoryMarshal.GetReference(keys),(nuint)i);
                order[i]=i; order[i+1]=i+1; order[i+2]=i+2; order[i+3]=i+3;
            }
        }
        for (; i < source.Length; i++)
        {
            Rectangle b=source[i].Bounds;
            double x=b.MinX*0.25+b.MaxX*0.25-minX, y=b.MinY*0.25+b.MaxY*0.25-minY;
            uint ix=width>0?(uint)Math.Clamp(finiteX?x*scaleX:x/width*65535,0,65535):0;
            uint iy=height>0?(uint)Math.Clamp(finiteY?y*scaleY:y/height*65535,0,65535):0;
            keys[i]=ix|(iy<<16);order[i]=i;
        }
        int vectorEnd=Vector256.IsHardwareAccelerated?source.Length&~7:0;
        for(i=0;i<vectorEnd;i+=8)
        {
            var xy=Vector256.LoadUnsafe(ref MemoryMarshal.GetReference(keys),(nuint)i);
            PackedHilbertOrder.Encode(xy&Vector256.Create(65535u),xy>>>16).StoreUnsafe(ref MemoryMarshal.GetReference(keys),(nuint)i);
        }
        for(;i<source.Length;i++)
        {
            uint xy=keys[i];keys[i]=HilbertOrder.Encode(xy&65535,xy>>16);
        }
    }
}
