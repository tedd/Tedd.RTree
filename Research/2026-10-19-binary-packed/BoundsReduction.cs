using System.Runtime.CompilerServices;
using System.Runtime.Intrinsics;

namespace Tedd.RTree;

internal static class BoundsReduction
{
    internal static Rectangle Entries<T>(ReadOnlySpan<SpatialEntry<T>> entries)
    {
        if(!Vector256.IsHardwareAccelerated)
        {
            Rectangle scalar=entries[0].Bounds;
            for(int i=1;i<entries.Length;i++)scalar=Rectangle.Union(scalar,entries[i].Bounds);
            return scalar;
        }
        Rectangle first=entries[0].Bounds;
        var min=Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref first));var max=min;
        for(int i=1;i<entries.Length;i++)
        {
            Rectangle box=entries[i].Bounds;
            var b=Vector256.LoadUnsafe(ref Unsafe.As<Rectangle,double>(ref box));
            min=Vector256.Min(min,b);max=Vector256.Max(max,b);
        }
        return new(min.GetElement(0),min.GetElement(1),max.GetElement(2),max.GetElement(3));
    }

    internal static Rectangle Boxes(ReadOnlySpan<Rectangle> boxes)
    {
        if(!Vector256.IsHardwareAccelerated)
        {
            Rectangle scalar=boxes[0];for(int i=1;i<boxes.Length;i++)scalar=Rectangle.Union(scalar,boxes[i]);return scalar;
        }
        ref double first=ref Unsafe.As<Rectangle,double>(ref System.Runtime.InteropServices.MemoryMarshal.GetReference(boxes));
        var min=Vector256.LoadUnsafe(ref first);var max=min;
        for(int i=1;i<boxes.Length;i++)
        {
            var b=Vector256.LoadUnsafe(ref first,(nuint)i*4);
            min=Vector256.Min(min,b);max=Vector256.Max(max,b);
        }
        return new(min.GetElement(0),min.GetElement(1),max.GetElement(2),max.GetElement(3));
    }
}
