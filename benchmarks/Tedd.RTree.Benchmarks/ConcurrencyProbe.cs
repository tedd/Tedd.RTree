using System.Diagnostics;
using Tedd.RTree;

internal static class ConcurrencyProbe
{
    private const int Size = 10_000;
    private const int Readers = 4;
    private const int DurationMs = 2_000;

    internal static void Run()
    {
        Console.WriteLine("Width,Mode,ReadsPerSecond,P50Us,P95Us,P99Us,MaxUs,WriterFrames,WriterBusyMs");
        foreach (string width in new[] { "Point", "Broad" })
            foreach (string mode in new[] { "Direct", "SnapshotIdle", "SnapshotWriter", "ImmediateWriter" })
                RunCase(width, mode);
    }

    private static void RunCase(string width, string mode)
    {
        Random random = new(73211);
        SpatialEntry<int>[] first = new SpatialEntry<int>[Size];
        SpatialEntry<int>[] second = new SpatialEntry<int>[Size];
        for (int i = 0; i < Size; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            Rectangle a = new(x, y, x + 1 + random.NextDouble() * 4, y + 1 + random.NextDouble() * 4);
            Rectangle b = new(a.MinX + 50, a.MinY + 50, a.MaxX + 50, a.MaxY + 50);
            first[i] = new SpatialEntry<int>(a, i);
            second[i] = new SpatialEntry<int>(b, i);
        }
        Rectangle[] queries = new Rectangle[64];
        double queryWidth = width == "Point" ? 0 : 1000;
        for (int i = 0; i < queries.Length; i++)
        {
            double x = random.NextDouble() * 1000;
            double y = random.NextDouble() * 1000;
            queries[i] = new Rectangle(x, y, x + queryWidth, y + queryWidth);
        }
        RTree<int> direct = new();
        direct.BulkLoad(first);
        SnapshotRTree<int> snapshot = new();
        snapshot.ReplaceAll(first);
        using ConcurrentRTree<int> immediate = new();
        immediate.BulkLoad(first);
        Func<Rectangle, List<int>, int> search = mode switch
        {
            "Direct" => direct.Search,
            "SnapshotIdle" or "SnapshotWriter" => snapshot.Search,
            _ => immediate.Search
        };

        using ManualResetEventSlim start = new(false);
        using CountdownEvent ready = new(Readers + (mode.EndsWith("Writer") ? 1 : 0));
        long deadline = 0;
        long[] counts = new long[Readers];
        List<double>[] samples = Enumerable.Range(0, Readers).Select(_ => new List<double>()).ToArray();
        Exception? failure = null;
        Thread[] readers = Enumerable.Range(0, Readers).Select(worker => new Thread(() =>
        {
            try
            {
                List<int> results = [];
                for (int i = 0; i < 64; i++)
                {
                    results.Clear();
                    search(queries[i], results);
                }
                ready.Signal();
                start.Wait();
                long count = 0;
                while (true)
                {
                    if ((count & 255) == 0 && Stopwatch.GetTimestamp() >= deadline) break;
                    Rectangle query = queries[(int)((count * 17 + worker) & 63)];
                    results.Clear();
                    if ((count & 63) == 0)
                    {
                        long before = Stopwatch.GetTimestamp();
                        int found = search(query, results);
                        samples[worker].Add((Stopwatch.GetTimestamp() - before) * 1_000_000.0 / Stopwatch.Frequency);
                        if (found != results.Count) throw new InvalidOperationException("Search count differs from list length.");
                    }
                    else
                        search(query, results);
                    count++;
                }
                counts[worker] = count;
            }
            catch (Exception ex) { Interlocked.CompareExchange(ref failure, ex, null); }
        }) { IsBackground = true }).ToArray();

        long writerFrames = 0;
        long writerTicks = 0;
        Thread? writer = null;
        if (mode.EndsWith("Writer"))
        {
            writer = new Thread(() =>
            {
                try
                {
                    ready.Signal();
                    start.Wait();
                    while (Stopwatch.GetTimestamp() < deadline)
                    {
                        SpatialEntry<int>[] entries = (writerFrames & 1) == 0 ? second : first;
                        long before = Stopwatch.GetTimestamp();
                        if (mode == "SnapshotWriter") snapshot.ReplaceAll(entries);
                        else
                            for (int i = 0; i < entries.Length; i++)
                                if (!immediate.Move(i, entries[i].Bounds))
                                    throw new InvalidOperationException("Move failed during concurrency probe.");
                        writerTicks += Stopwatch.GetTimestamp() - before;
                        writerFrames++;
                        Thread.Sleep(10);
                    }
                }
                catch (Exception ex) { Interlocked.CompareExchange(ref failure, ex, null); }
            }) { IsBackground = true };
        }

        foreach (Thread reader in readers) reader.Start();
        writer?.Start();
        ready.Wait();
        long began = Stopwatch.GetTimestamp();
        deadline = began + DurationMs * Stopwatch.Frequency / 1_000;
        start.Set();
        foreach (Thread reader in readers) reader.Join();
        long readersEnded = Stopwatch.GetTimestamp();
        writer?.Join();
        if (failure is not null) throw failure;

        double elapsed = (readersEnded - began) / (double)Stopwatch.Frequency;
        double[] sorted = samples.SelectMany(x => x).Order().ToArray();
        static double Percentile(double[] values, double fraction) => values[(int)Math.Floor((values.Length - 1) * fraction)];
        Console.WriteLine(FormattableString.Invariant($"{width},{mode},{counts.Sum() / elapsed:F0},{Percentile(sorted, 0.50):F3},{Percentile(sorted, 0.95):F3},{Percentile(sorted, 0.99):F3},{sorted[^1]:F3},{writerFrames},{writerTicks * 1_000.0 / Stopwatch.Frequency:F1}"));
    }
}
