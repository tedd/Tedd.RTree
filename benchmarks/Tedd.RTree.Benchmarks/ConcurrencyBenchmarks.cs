using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using Tedd.RTree;

// Search-only experiment: the tree is fully built before any worker starts.
[ShortRunJob]
[MemoryDiagnoser]
public class ParallelSearchBenchmarks
{
    [Params(1, 64, 1024)] public int QueryCount { get; set; }
    [Params("Point", "Broad")] public string Width { get; set; } = "Point";

    private RTree<int> _tree = null!;
    private Rectangle[] _queries = null!;
    private readonly List<int>[] _results = Enumerable.Range(0, 8).Select(_ => new List<int>()).ToArray();
    private readonly int[] _counts = new int[8];
    private readonly ParallelOptions _four = new() { MaxDegreeOfParallelism = 4 };
    private readonly ParallelOptions _eight = new() { MaxDegreeOfParallelism = 8 };

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        SpatialEntry<int>[] entries = new SpatialEntry<int>[10_000];
        for (int i = 0; i < entries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            entries[i] = new SpatialEntry<int>(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _queries = new Rectangle[QueryCount];
        double width = Width == "Point" ? 0 : 1000;
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _queries[i] = new Rectangle(x, y, x + width, y + width);
        }
        int expected = Sequential();
        if (Parallel4() != expected || Parallel8() != expected)
            throw new InvalidOperationException("Parallel search returned a different result count.");
    }

    [Benchmark(Baseline = true)]
    public int Sequential()
    {
        List<int> results = _results[0];
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            results.Clear();
            total += _tree.Search(query, results);
        }
        return total;
    }

    [Benchmark] public int Parallel4() => ParallelSearch(4, _four);
    [Benchmark] public int Parallel8() => ParallelSearch(8, _eight);

    private int ParallelSearch(int degree, ParallelOptions options)
    {
        Parallel.For(0, degree, options, worker =>
        {
            List<int> results = _results[worker];
            int count = 0;
            for (int i = worker; i < _queries.Length; i += degree)
            {
                results.Clear();
                count += _tree.Search(_queries[i], results);
            }
            _counts[worker] = count;
        });
        int total = 0;
        for (int i = 0; i < degree; i++) total += _counts[i];
        return total;
    }
}

// Same queries and results; only the synchronization/publication mechanism differs.
[ShortRunJob]
[MemoryDiagnoser]
public class SearchWrapperBenchmarks
{
    [Params("Point", "Broad")] public string Width { get; set; } = "Point";

    private RTree<int> _tree = null!;
    private SnapshotRTree<int> _snapshot = null!;
    private readonly ReaderWriterLockSlim _rwLock = new();
    private Rectangle[] _queries = null!;
    private readonly List<int> _results = [];

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        SpatialEntry<int>[] entries = new SpatialEntry<int>[10_000];
        for (int i = 0; i < entries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            entries[i] = new SpatialEntry<int>(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
        }
        _tree = new RTree<int>();
        _tree.BulkLoad(entries);
        _snapshot = new SnapshotRTree<int>();
        _snapshot.ReplaceAll(entries);
        _queries = new Rectangle[64];
        double width = Width == "Point" ? 0 : 1000;
        for (int i = 0; i < _queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            _queries[i] = new Rectangle(x, y, x + width, y + width);
        }
        int expected = Direct();
        if (Snapshot() != expected || ReaderWriterLock() != expected)
            throw new InvalidOperationException("Wrapped search returned a different result count.");
    }

    [Benchmark(Baseline = true)] public int Direct() => Query(0);
    [Benchmark] public int Snapshot() => Query(1);
    [Benchmark] public int ReaderWriterLock() => Query(2);

    private int Query(int mode)
    {
        int total = 0;
        foreach (Rectangle query in _queries)
        {
            _results.Clear();
            if (mode == 0) total += _tree.Search(query, _results);
            else if (mode == 1) total += _snapshot.Search(query, _results);
            else
            {
                _rwLock.EnterReadLock();
                try { total += _tree.Search(query, _results); }
                finally { _rwLock.ExitReadLock(); }
            }
        }
        return total;
    }
}

[ShortRunJob]
[MemoryDiagnoser]
public class MovingUpdateBenchmarks
{
    [Params(100, 1_000, 10_000)] public int MovedCount { get; set; }

    private SpatialEntry<int>[] _a = null!;
    private SpatialEntry<int>[] _b = null!;
    private SnapshotRTree<int> _snapshot = null!;
    private ConcurrentRTree<int> _mutable = null!;
    private bool _snapshotPhase;
    private bool _mutablePhase;

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        _a = new SpatialEntry<int>[10_000];
        _b = new SpatialEntry<int>[10_000];
        for (int i = 0; i < _a.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            Rectangle original = new(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            Rectangle moved = i < MovedCount
                ? new Rectangle(original.MinX + 50, original.MinY + 50, original.MaxX + 50, original.MaxY + 50)
                : original;
            _a[i] = new SpatialEntry<int>(original, i);
            _b[i] = new SpatialEntry<int>(moved, i);
        }
        _snapshot = new SnapshotRTree<int>();
        _snapshot.ReplaceAll(_a);
        _mutable = new ConcurrentRTree<int>();
        _mutable.BulkLoad(_a);
        if (_snapshot.Count != _mutable.Count) throw new InvalidOperationException("Initial counts differ.");
        // Exercise a full move cycle and compare both indexes before timing.
        ToggleSnapshot();
        ToggleMutable();
        for (int i = 0; i < 64; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            Rectangle query = new(x, y, x + 100, y + 100);
            if (!_snapshot.Search(query).Order().SequenceEqual(_mutable.Search(query).Order()))
                throw new InvalidOperationException("Moved indexes differ.");
        }
        ToggleSnapshot();
        ToggleMutable();
    }

    [GlobalCleanup] public void Cleanup() => _mutable.Dispose();

    [Benchmark(Baseline = true)] public int SnapshotReplace() => ToggleSnapshot();
    [Benchmark] public int ImmediateMoves() => ToggleMutable();

    private int ToggleSnapshot()
    {
        _snapshotPhase = !_snapshotPhase;
        _snapshot.ReplaceAll(_snapshotPhase ? _b : _a);
        return _snapshot.Count;
    }

    private int ToggleMutable()
    {
        _mutablePhase = !_mutablePhase;
        SpatialEntry<int>[] entries = _mutablePhase ? _b : _a;
        for (int i = 0; i < MovedCount; i++)
            if (!_mutable.Move(i, entries[i].Bounds))
                throw new InvalidOperationException("Indexed value vanished during move.");
        return _mutable.Count;
    }
}

// Four independent trees provide a concrete single-query partition without modifying RTree internals.
[ShortRunJob]
[MemoryDiagnoser]
public class ShardedSearchBenchmarks
{
    [Params("Point", "Broad")] public string Width { get; set; } = "Point";

    private RTree<int> _whole = null!;
    private RTree<int>[] _shards = null!;
    private Rectangle _query;
    private readonly List<int> _merged = [];
    private readonly List<int>[] _parts = Enumerable.Range(0, 4).Select(_ => new List<int>()).ToArray();
    private readonly ParallelOptions _parallel = new() { MaxDegreeOfParallelism = 4 };

    [GlobalSetup]
    public void Setup()
    {
        Random random = new(73211);
        SpatialEntry<int>[] entries = new SpatialEntry<int>[10_000];
        List<SpatialEntry<int>>[] partitions = Enumerable.Range(0, 4).Select(_ => new List<SpatialEntry<int>>()).ToArray();
        for (int i = 0; i < entries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            SpatialEntry<int> entry = new(new Rectangle(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4), i);
            entries[i] = entry;
            partitions[i & 3].Add(entry);
        }
        _whole = new RTree<int>();
        _whole.BulkLoad(entries);
        _shards = partitions.Select(part =>
        {
            RTree<int> tree = new();
            tree.BulkLoad(part);
            return tree;
        }).ToArray();
        double width = Width == "Point" ? 0 : 1000;
        _query = new Rectangle(250, 250, 250 + width, 250 + width);
        Direct();
        int[] expected = _merged.Order().ToArray();
        SequentialShards();
        if (!_merged.Order().SequenceEqual(expected)) throw new InvalidOperationException("Sequential shards differ.");
        ParallelShards();
        if (!_merged.Order().SequenceEqual(expected)) throw new InvalidOperationException("Parallel shards differ.");
    }

    [Benchmark(Baseline = true)]
    public int Direct()
    {
        _merged.Clear();
        return _whole.Search(_query, _merged);
    }

    [Benchmark]
    public int SequentialShards()
    {
        _merged.Clear();
        foreach (RTree<int> shard in _shards) shard.Search(_query, _merged);
        return _merged.Count;
    }

    [Benchmark]
    public int ParallelShards()
    {
        _merged.Clear();
        Parallel.For(0, 4, _parallel, i =>
        {
            List<int> part = _parts[i];
            part.Clear();
            _shards[i].Search(_query, part);
        });
        foreach (List<int> part in _parts) _merged.AddRange(part);
        return _merged.Count;
    }
}
