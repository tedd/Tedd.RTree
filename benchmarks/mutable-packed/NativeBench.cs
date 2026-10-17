using System.Diagnostics;
using System.Runtime.InteropServices;
using Tedd.RTree;

internal static unsafe class NativeBench
{
    [StructLayout(LayoutKind.Sequential)]
    private readonly record struct Rect(double X, double Y, double MaxX, double MaxY);
    [StructLayout(LayoutKind.Sequential)]
    private readonly struct View { internal readonly int* Pointer; internal readonly nuint Count; }

    [DllImport("packed_native", CallingConvention = CallingConvention.Cdecl, EntryPoint = "index_create")]
    private static extern nint Create(uint mode, Rect* boxes, nuint count);
    [DllImport("packed_native", CallingConvention = CallingConvention.Cdecl, EntryPoint = "index_destroy")]
    private static extern void Destroy(nint context);
    [DllImport("packed_native", CallingConvention = CallingConvention.Cdecl, EntryPoint = "index_query")]
    private static extern void Query(nint context, Rect query);
    [DllImport("packed_native", CallingConvention = CallingConvention.Cdecl, EntryPoint = "index_result"), SuppressGCTransition]
    private static extern View Results(nint context);
    [DllImport("packed_native", CallingConvention = CallingConvention.Cdecl, EntryPoint = "index_query_leaf"), SuppressGCTransition]
    private static extern void QueryLeaf(nint context, Rect query);

    internal static void Run(Rectangle[] bounds, Rectangle[] queries, string mode)
    {
        NativeLibrary.SetDllImportResolver(typeof(NativeBench).Assembly, (name, _, _) =>
            name == "packed_native" ? NativeLibrary.Load(Environment.GetEnvironmentVariable("PACKED_NATIVE_PATH")!) : 0);
        uint kind = mode switch { "native-static" => 0, "native-geo-hilbert" => 1, "native-geo-str" => 2, _ => throw new ArgumentException("native mode") };
        var boxes = bounds.Select(b => new Rect(b.MinX, b.MinY, b.MaxX, b.MaxY)).ToArray();
        var qs = queries.Select(b => new Rect(b.MinX, b.MinY, b.MaxX, b.MaxY)).ToArray();
        nint Build() { fixed (Rect* p = boxes) return Create(kind, p, (nuint)boxes.Length); }
        nint ctx = Build();
        ReadOnlySpan<int> Search(int q)
        {
            if (kind == 0 && boxes.Length <= 16) QueryLeaf(ctx, qs[q]); else Query(ctx, qs[q]);
            var result = Results(ctx);
            return new ReadOnlySpan<int>(result.Pointer, checked((int)result.Count));
        }
        long sink = 0;
        void Measure(string name, Func<long> action)
        {
            int repetitions = 1;
            double Block() { var sw = Stopwatch.StartNew(); for (int i = 0; i < repetitions; i++) sink ^= action(); return sw.Elapsed.TotalMilliseconds; }
            while (Block() < 100) repetitions *= 2;
            Console.WriteLine($"{name},{Block() * 1000 / repetitions:R},{repetitions},NA");
        }
        try
        {
            for (int q = 0; q < qs.Length; q++)
            {
                var actual = Search(q).ToArray(); Array.Sort(actual);
                var expected = Enumerable.Range(0, bounds.Length).Where(i => bounds[i].Intersects(queries[q])).ToArray();
                if (!actual.SequenceEqual(expected)) throw new Exception("Interop result-set mismatch.");
            }
            Measure("build", () => { nint built = Build(); Destroy(built); return boxes.Length; });
            for (int g = 0; g < 4; g++)
            {
                int group = g;
                Measure($"query{g}", () => { long sum = 0; for (int q = group; q < qs.Length; q += 4) foreach (int id in Search(q)) sum += id + 1; return sum; });
            }
            Console.Error.WriteLine($"validated={qs.Length};sink={sink}");
        }
        finally { Destroy(ctx); }
    }
}
