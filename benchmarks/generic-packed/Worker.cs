using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using Tedd.RTree;

CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
switch (args[1])
{
    case "int": Bench.Run<int>(args); break;
    case "long": Bench.Run<long>(args); break;
    case "float": Bench.Run<float>(args); break;
    case "double": Bench.Run<double>(args); break;
    default: throw new ArgumentException("Coordinate type");
}

internal static class Bench
{
    internal static int MoveScale = 1;
    internal readonly record struct Bounds(int X, int Y, int Z, int MaxX, int MaxY, int MaxZ)
    {
        internal bool Intersects(Bounds b, int dimension) => X <= b.MaxX && MaxX >= b.X && Y <= b.MaxY && MaxY >= b.Y &&
            (dimension == 2 || Z <= b.MaxZ && MaxZ >= b.Z);
        internal Bounds Moved => new(X + 7 * MoveScale, Y - 9 * MoveScale, Z + 11 * MoveScale, MaxX + 7 * MoveScale, MaxY - 9 * MoveScale, MaxZ + 11 * MoveScale);
    }
    internal interface IIndex : IDisposable { int Count { get; } void Search(int q, List<int> results); bool Move(int id); }

    internal static void Run<C>(string[] args) where C : struct, INumber<C>
    {
        int dimension = int.Parse(args[0]), n = int.Parse(args[2]);
        string distribution = args[3], mode = args[4], action = args.Length > 5 ? args[5] : "measure";
        MoveScale = args.Length > 6 ? int.Parse(args[6]) : 1;
        int guardMask = args.Length > 7 ? int.Parse(args[7]) : 0;
        uint state = 73211;
        int Next(int limit) { state = unchecked(state * 1664525 + 1013904223); return (int)((state >> 8) % (uint)limit); }
        var boxes = new Bounds[n]; var queries = new Bounds[64];
        for (int i = 0; i < n; i++)
        {
            int Coord() => distribution == "clustered" ? (i % 8) * 125 + Next(30) : Next(1000);
            int x = Coord(), y = Coord(), z = Coord();
            boxes[i] = new(x, y, z, x + Next(5) + 1, y + Next(5) + 1, z + Next(5) + 1);
        }
        for (int i = 0; i < queries.Length; i++)
        {
            int x = Next(1000), y = Next(1000), z = Next(1000), width = new[] { 0, 20, 200, 1000 }[i % 4];
            queries[i] = new(x, y, z, x + width, y + width, z + width);
        }
        // Include nonempty points, inclusive contacts, and complete containment in every fixture.
        queries[0] = new(boxes[0].X, boxes[0].Y, boxes[0].Z, boxes[0].X, boxes[0].Y, boxes[0].Z);
        queries[4] = new(boxes[0].MaxX, boxes[0].MaxY, boxes[0].MaxZ, boxes[0].MaxX, boxes[0].MaxY, boxes[0].MaxZ);
        queries[3] = new(-1, -1, -1, 2000, 2000, 2000);
        Func<IIndex> factory;
        if (dimension == 2)
        {
            var entries = boxes.Select((b, i) => new SpatialEntry2D<C, int>(Rect<C>(b), i)).ToArray();
            var qs = queries.Select(Rect<C>).ToArray();
            if (mode == "original")
            {
                var originalEntries = boxes.Select((b, i) => new SpatialEntry<int>(new(b.X, b.Y, b.MaxX, b.MaxY), i)).ToArray();
                var originalQueries = queries.Select(b => new Rectangle(b.X, b.Y, b.MaxX, b.MaxY)).ToArray();
                factory = () => new OriginalIndex(originalEntries, originalQueries);
            }
            else factory = () => new Index2<C>(entries, qs, mode);
        }
        else
        {
            var entries = boxes.Select((b, i) => new SpatialEntry3D<C, int>(Box<C>(b), i)).ToArray();
            var qs = queries.Select(Box<C>).ToArray();
            factory = () => new Index3<C>(entries, qs, mode);
        }
        using IIndex tree = factory();
        var output = new List<int>(n); long sink = 0; ulong shape = 14695981039346656037UL;
        void Verify()
        {
            if (tree.Count != n) throw new Exception("Count mismatch");
            for (int q = 0; q < queries.Length; q++)
            {
                output.Clear(); tree.Search(q, output);
                foreach (int id in output) shape = unchecked((shape ^ (uint)(id + 1)) * 1099511628211UL);
                var expected = Enumerable.Range(0, n).Where(i => boxes[i].Intersects(queries[q], dimension));
                if (!output.Order().SequenceEqual(expected)) throw new Exception("Result-set mismatch");
            }
        }
        long Query(int group)
        {
            long sum = 0;
            for (int q = group; q < queries.Length; q += 4)
            {
                output.Clear(); tree.Search(q, output);
                foreach (int id in output) sum += id + 1;
            }
            return sum;
        }
        long Build() { using var built = factory(); return built.Count; }
        void Measure(string name, Func<long> operation)
        {
            int repetitions = 1;
            double Block() { var sw = Stopwatch.StartNew(); for (int i = 0; i < repetitions; i++) sink ^= operation(); return sw.Elapsed.TotalMilliseconds; }
            int milliseconds = action == "guard" && ((name == "build" && (guardMask & 1) != 0) ||
                (name == "queryall" && (guardMask & 2) != 0) || (name == "mutatedall" && (guardMask & 4) != 0)) ? 1000 : 100;
            while (Block() < milliseconds) repetitions *= 2;
            long allocation = GC.GetAllocatedBytesForCurrentThread();
            double elapsed = Block(); allocation = GC.GetAllocatedBytesForCurrentThread() - allocation;
            Console.WriteLine($"{name},{elapsed * 1000 / repetitions:R},{repetitions},{(double)allocation / repetitions:R}");
        }
        Verify();
        if (action == "guard")
        {
            long QueryAll() { long sum = 0; for (int g = 0; g < 4; g++) sum += Query(g); return sum; }
            Measure("queryall", QueryAll);
            if (mode != "snapshot")
            {
                using (var warm = factory()) for (int i = 0; i < Math.Min(64, n); i++) if (!warm.Move(i)) throw new Exception("Guard warm move failed");
                long allocation = GC.GetAllocatedBytesForCurrentThread(); var sw = Stopwatch.StartNew();
                for (int i = 0; i < Math.Min(1000, n); i++) if (!tree.Move(i)) throw new Exception("Guard move failed");
                double elapsed = sw.Elapsed.TotalMicroseconds; allocation = GC.GetAllocatedBytesForCurrentThread() - allocation;
                Console.WriteLine($"mutation,{elapsed:R},1,{allocation}");
                for (int i = 0; i < Math.Min(1000, n); i++) boxes[i] = boxes[i].Moved;
                Verify();
                Measure("mutatedall", QueryAll);
            }
            Measure("build", Build);
            Console.Error.WriteLine($"validated={(mode == "snapshot" ? 64 : 128)};sink={sink};shape={shape:x16}");
            return;
        }
        if (action == "codegen") { Build(); for (int g = 0; g < 4; g++) sink ^= Query(g); Console.WriteLine(sink); return; }
        if (action.StartsWith("profile-"))
        {
            Console.WriteLine($"READY {Environment.ProcessId}"); Console.Out.Flush();
            var sw = Stopwatch.StartNew(); while (sw.Elapsed.TotalSeconds < 45)
                if (action == "profile-build") sink ^= Build();
                else if (action == "profile-mutation")
                {
                    using var moved = factory();
                    for (int i = 0; i < Math.Min(1000, n); i++) if (!moved.Move(i)) throw new Exception("Profile move failed");
                    sink ^= moved.Count;
                }
                else for (int g = 0; g < 4; g++) sink ^= Query(g);
            Console.WriteLine(sink); return;
        }
        Measure("build", Build);
        for (int g = 0; g < 4; g++) { int group = g; Measure($"query{g}", () => Query(group)); }
        if (mode != "snapshot")
        {
            using (var warm = factory()) for (int i = 0; i < Math.Min(64, n); i++) if (!warm.Move(i)) throw new Exception("Warm move failed");
            long allocation = GC.GetAllocatedBytesForCurrentThread(); var sw = Stopwatch.StartNew();
            for (int i = 0; i < Math.Min(1000, n); i++) if (!tree.Move(i)) throw new Exception("Move failed");
            double elapsed = sw.Elapsed.TotalMicroseconds; allocation = GC.GetAllocatedBytesForCurrentThread() - allocation;
            Console.WriteLine($"mutation,{elapsed:R},1,{allocation}");
            for (int i = 0; i < Math.Min(1000, n); i++) boxes[i] = boxes[i].Moved;
            Verify();
            for (int g = 0; g < 4; g++) { int group = g; Measure($"mutated{g}", () => Query(group)); }
        }
        Console.Error.WriteLine($"validated={(mode == "snapshot" ? 64 : 128)};sink={sink};shape={shape:x16}");
    }

    private static Rectangle2D<C> Rect<C>(Bounds b) where C : struct, INumber<C> => new(C.CreateChecked(b.X), C.CreateChecked(b.Y), C.CreateChecked(b.MaxX), C.CreateChecked(b.MaxY));
    private static Box<C> Box<C>(Bounds b) where C : struct, INumber<C> => new(C.CreateChecked(b.X), C.CreateChecked(b.Y), C.CreateChecked(b.Z), C.CreateChecked(b.MaxX), C.CreateChecked(b.MaxY), C.CreateChecked(b.MaxZ));

    private sealed class OriginalIndex : IIndex
    {
        private readonly RTree<int> _tree = new();
        private readonly SpatialEntry<int>[] _entries;
        private readonly Rectangle[] _queries;
        public OriginalIndex(SpatialEntry<int>[] entries, Rectangle[] queries)
        { _entries = entries; _queries = queries; _tree.BulkLoad(entries); }
        public int Count => _tree.Count;
        public void Search(int q, List<int> output) => _tree.Search(_queries[q], output);
        public bool Move(int id)
        {
            var b = _entries[id].Bounds;
            return _tree.Update(b, id, new(b.MinX + 7 * MoveScale, b.MinY - 9 * MoveScale, b.MaxX + 7 * MoveScale, b.MaxY - 9 * MoveScale));
        }
        public void Dispose() { }
    }

    private sealed class Index2<C> : IIndex where C : struct, INumber<C>
    {
        private readonly RTree2D<C, int>? _plain;
        private readonly SnapshotRTree2D<C, int>? _snapshot;
        private readonly ConcurrentRTree2D<C, int>? _concurrent;
        private readonly SpatialEntry2D<C, int>[] _entries;
        private readonly Rectangle2D<C>[] _queries;
        public Index2(SpatialEntry2D<C, int>[] entries, Rectangle2D<C>[] queries, string mode)
        {
            _entries = entries; _queries = queries;
            switch (mode) {
                case "plain": _plain = new(); _plain.BulkLoad(entries); break;
                case "snapshot": _snapshot = new(); _snapshot.ReplaceAll(entries); break;
                case "concurrent": _concurrent = new(); _concurrent.BulkLoad(entries); break;
                default: throw new ArgumentException("Mode");
            }
        }
        public int Count => _plain?.Count ?? _snapshot?.Count ?? _concurrent!.Count;
        public void Search(int q, List<int> output)
        { if (_plain is not null) _plain.Search(_queries[q], output); else if (_snapshot is not null) _snapshot.Search(_queries[q], output); else _concurrent!.Search(_queries[q], output); }
        public bool Move(int id)
        {
            var b = _entries[id].Bounds; var moved = new Rectangle2D<C>(b.MinX + C.CreateChecked(7 * MoveScale), b.MinY - C.CreateChecked(9 * MoveScale), b.MaxX + C.CreateChecked(7 * MoveScale), b.MaxY - C.CreateChecked(9 * MoveScale));
            return _plain is not null ? _plain.Update(b, id, moved) : _concurrent!.Move(id, moved);
        }
        public void Dispose() => _concurrent?.Dispose();
    }
    private sealed class Index3<C> : IIndex where C : struct, INumber<C>
    {
        private readonly RTree3D<C, int>? _plain;
        private readonly SnapshotRTree3D<C, int>? _snapshot;
        private readonly ConcurrentRTree3D<C, int>? _concurrent;
        private readonly SpatialEntry3D<C, int>[] _entries;
        private readonly Box<C>[] _queries;
        public Index3(SpatialEntry3D<C, int>[] entries, Box<C>[] queries, string mode)
        {
            _entries = entries; _queries = queries;
            switch (mode) {
                case "plain": _plain = new(); _plain.BulkLoad(entries); break;
                case "snapshot": _snapshot = new(); _snapshot.ReplaceAll(entries); break;
                case "concurrent": _concurrent = new(); _concurrent.BulkLoad(entries); break;
                default: throw new ArgumentException("Mode");
            }
        }
        public int Count => _plain?.Count ?? _snapshot?.Count ?? _concurrent!.Count;
        public void Search(int q, List<int> output)
        { if (_plain is not null) _plain.Search(_queries[q], output); else if (_snapshot is not null) _snapshot.Search(_queries[q], output); else _concurrent!.Search(_queries[q], output); }
        public bool Move(int id)
        {
            var b = _entries[id].Bounds; var moved = new Box<C>(b.MinX + C.CreateChecked(7 * MoveScale), b.MinY - C.CreateChecked(9 * MoveScale), b.MinZ + C.CreateChecked(11 * MoveScale), b.MaxX + C.CreateChecked(7 * MoveScale), b.MaxY - C.CreateChecked(9 * MoveScale), b.MaxZ + C.CreateChecked(11 * MoveScale));
            return _plain is not null ? _plain.Update(b, id, moved) : _concurrent!.Move(id, moved);
        }
        public void Dispose() => _concurrent?.Dispose();
    }
}
