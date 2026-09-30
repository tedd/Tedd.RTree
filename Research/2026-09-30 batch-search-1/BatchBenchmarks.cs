using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Jobs;
using Tedd.RTree;

[ShortRunJob]
[MemoryDiagnoser]
public class BatchBenchmarks
{
    [Params("Point", "Miss")]
    public string Shape { get; set; } = "Point";
    private Fixture _fixture = null!;
    private ConcurrentRTree<int> _concurrent = null!;
    private SnapshotRTree<int> _snapshot = null!;
    private List<int>[] _outputs = null!;
    private int[] _counts = null!;

    [GlobalSetup]
    public void Setup()
    {
        _fixture = new(Shape, false);
        _concurrent = new(); _concurrent.BulkLoad(_fixture.Entries);
        _snapshot = new(); _snapshot.ReplaceAll(_fixture.Entries);
        _outputs = _fixture.Queries.Select(q => new List<int>()).ToArray();
        _counts = new int[_outputs.Length];
        long a = ConcurrentSingles(), b = ConcurrentBatch(), c = SnapshotSingles(), d = SnapshotBatch();
        if (a != b || b != c || c != d) throw new InvalidOperationException("Batch oracle failed.");
    }

    [GlobalCleanup] public void Cleanup() => _concurrent.Dispose();
    private void Clear() { foreach (var output in _outputs) output.Clear(); }
    [Benchmark(Baseline = true)]
    public long ConcurrentSingles()
    {
        Clear();
        long total = 0;
        for (int i = 0; i < _outputs.Length; i++) total += _concurrent.Search(_fixture.Queries[i], _outputs[i]);
        return total;
    }
    [Benchmark] public long ConcurrentBatch() { Clear(); return _concurrent.SearchBatch(_fixture.Queries, _outputs, _counts); }
    [Benchmark]
    public long SnapshotSingles()
    {
        Clear();
        long total = 0;
        for (int i = 0; i < _outputs.Length; i++) total += _snapshot.Search(_fixture.Queries[i], _outputs[i]);
        return total;
    }
    [Benchmark] public long SnapshotBatch() { Clear(); return _snapshot.SearchBatch(_fixture.Queries, _outputs, _counts); }
}
