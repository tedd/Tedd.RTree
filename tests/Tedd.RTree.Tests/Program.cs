using Tedd.RTree;

static void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}

static Rectangle RandomRectangle(Random random)
{
    double x = random.NextDouble() * 1000 - 500;
    double y = random.NextDouble() * 1000 - 500;
    return new Rectangle(x, y, x + random.NextDouble() * 20, y + random.NextDouble() * 20);
}

Check(new Rectangle(0, 0, 1, 1).Intersects(new Rectangle(1, 1, 2, 2)), "Edges must intersect.");
Check(new Rectangle(0, 0, 2, 2).Contains(new Rectangle(1, 1, 2, 2)), "Inclusive containment.");
RTree<int> duplicateTree = new(4);
duplicateTree.Insert(new Rectangle(0, 0, 1, 1), 7);
duplicateTree.Insert(new Rectangle(0, 0, 1, 1), 7);
Check(duplicateTree.Remove(new Rectangle(0, 0, 1, 1), 7) && duplicateTree.Count == 1 &&
    duplicateTree.Search(new Rectangle(0, 0, 1, 1)).Single() == 7, "Remove one duplicate.");
foreach (double invalid in new[] { double.NaN, double.PositiveInfinity, double.NegativeInfinity })
{
    try { _ = new Rectangle(invalid, 0, 1, 1); throw new Exception("Invalid coordinate accepted."); }
    catch (ArgumentOutOfRangeException) { }
}
try { _ = new Rectangle(2, 0, 1, 1); throw new Exception("Reversed bounds accepted."); }
catch (ArgumentOutOfRangeException) { }
try { _ = new RTree<int>(3); throw new Exception("Invalid capacity accepted."); }
catch (ArgumentOutOfRangeException) { }

foreach (int capacity in new[] { 4, 5, 8, 16, 32 })
{
    RTree<int> tree = new(capacity);
    List<(Rectangle Bounds, int Id)> reference = [];
    List<int> results = [];
    Random random = new(20260926 + capacity);
    Check(tree.Search(new Rectangle(0, 0, 1, 1), results) == 0, "Empty search.");
    for (int i = 0; i < 2000; i++)
    {
        Rectangle bounds = i % 17 == 0 ? new Rectangle(0, 0, 1, 1) : RandomRectangle(random);
        tree.Insert(bounds, i);
        reference.Add((bounds, i));
        Check(tree.Count == i + 1, "Count after insert.");
        if (i % 37 != 0) continue;
        for (int q = 0; q < 25; q++)
        {
            Rectangle query = q % 5 == 0 ? new Rectangle(1, 1, 1, 1) : RandomRectangle(random);
            results.Clear();
            int count = tree.Search(query, results);
            int[] expected = reference.Where(item => item.Bounds.Intersects(query)).Select(item => item.Id).Order().ToArray();
            Check(count == expected.Length, $"Count mismatch: capacity={capacity}, insert={i}, query={q}.");
            Check(results.Order().SequenceEqual(expected), $"Result mismatch: capacity={capacity}, insert={i}, query={q}.");
        }
    }
    results.Clear();
    Rectangle everything = new(-1000, -1000, 1000, 1000);
    Check(tree.Search(everything, results) == reference.Count, "Full search.");
    Check(tree.Search(everything).Count == reference.Count, "Allocating search.");
    tree.Clear();
    results.Clear();
    Check(tree.Count == 0 && tree.Search(everything, results) == 0, "Clear.");
    tree.Insert(new Rectangle(0, 0, 0, 0), 99);
    Check(tree.Search(everything, results) == 1 && results[0] == 99, "Reuse after clear.");

    tree.Clear();
    SpatialEntry<int>[] batch = reference.Select(item => new SpatialEntry<int>(item.Bounds, item.Id)).ToArray();
    tree.BulkLoad(batch);
    Check(tree.Count == batch.Length, "Bulk count.");
    for (int q = 0; q < 250; q++)
    {
        Rectangle query = q % 5 == 0 ? new Rectangle(1, 1, 1, 1) : RandomRectangle(random);
        int[] expected = reference.Where(item => item.Bounds.Intersects(query)).Select(item => item.Id).Order().ToArray();
        Check(tree.Search(query).Order().SequenceEqual(expected), $"Bulk result mismatch: capacity={capacity}, query={q}.");
    }
    tree.Insert(new Rectangle(0, 0, 0, 0), 2001);
    Check(tree.Search(new Rectangle(0, 0, 0, 0)).Contains(2001), "Insert after bulk load.");
    try { tree.BulkLoad(batch); throw new Exception("Bulk loading into nonempty tree accepted."); }
    catch (InvalidOperationException) { }
    Check(tree.Remove(new Rectangle(0, 0, 0, 0), 2001), "Remove after bulk load.");
    Check(!tree.Remove(new Rectangle(0, 0, 0, 0), 2001), "Missing item removal.");
    for (int move = 0; move < 300; move++)
    {
        int id = move * 7 % reference.Count;
        Rectangle oldBounds = reference[id].Bounds;
        Rectangle newBounds = RandomRectangle(random);
        Check(tree.Update(oldBounds, id, newBounds), "Move existing entry.");
        reference[id] = (newBounds, id);
        if (move % 10 != 0) continue;
        for (int q = 0; q < 25; q++)
        {
            Rectangle query = RandomRectangle(random);
            int[] expected = reference.Where(item => item.Bounds.Intersects(query)).Select(item => item.Id).Order().ToArray();
            Check(tree.Search(query).Order().SequenceEqual(expected),
                $"Move result mismatch: capacity={capacity}, move={move}, query={q}.");
        }
    }
    Check(!tree.Update(new Rectangle(0, 0, 0, 0), -1, new Rectangle(1, 1, 1, 1)), "Missing item move.");
    foreach (int id in Enumerable.Range(0, reference.Count).OrderBy(_ => random.Next()))
        Check(tree.Remove(reference[id].Bounds, id), $"Remove existing entry: capacity={capacity}, id={id}.");
    Check(tree.Count == 0 && tree.Search(everything).Count == 0, "All entries removed.");
}

RTree<int> emptyBulk = new();
emptyBulk.BulkLoad(Array.Empty<SpatialEntry<int>>());
Check(emptyBulk.Count == 0, "Empty bulk load.");
foreach (int size in new[] { 1, 3, 4, 5, 15, 16, 17, 128, 129 })
{
    SpatialEntry<int>[] items = Enumerable.Range(0, size)
        .Select(i => new SpatialEntry<int>(new Rectangle(i, i, i + 1, i + 1), i)).ToArray();
    RTree<int> tree = new(16);
    tree.BulkLoad(items);
    Check(tree.Search(new Rectangle(-1, -1, size + 1, size + 1)).Order().SequenceEqual(Enumerable.Range(0, size)),
        $"Bulk packing boundary: {size}.");
    BulkLoadWorkspace workspace = new(Math.Max(0, size - 1));
    RTree<int> workspaceTree = new(16);
    workspaceTree.BulkLoad(items, workspace);
    Check(workspace.Capacity >= size, $"Workspace growth: {size}.");
    Check(workspaceTree.Search(new Rectangle(-1, -1, size + 1, size + 1)).Order().SequenceEqual(Enumerable.Range(0, size)),
        $"Workspace bulk packing boundary: {size}.");
}
BulkLoadWorkspace reusedWorkspace = new(129);
foreach (int size in new[] { 129, 5, 128 })
{
    SpatialEntry<int>[] items = Enumerable.Range(0, size)
        .Select(i => new SpatialEntry<int>(new Rectangle(i, i, i + 1, i + 1), i)).ToArray();
    RTree<int> tree = new(16);
    tree.BulkLoad(items, reusedWorkspace);
    Check(tree.Search(new Rectangle(-1, -1, 130, 130)).Order().SequenceEqual(Enumerable.Range(0, size)),
        $"Workspace reuse across batch sizes: {size}.");
}
try { _ = new BulkLoadWorkspace(-1); throw new Exception("Negative workspace capacity accepted."); }
catch (ArgumentOutOfRangeException) { }
try { new RTree<int>().BulkLoad([], null!); throw new Exception("Null workspace accepted."); }
catch (ArgumentNullException) { }

RTree<int> extremeTree = new(4);
extremeTree.Insert(new Rectangle(-double.MaxValue, -double.MaxValue, -double.MaxValue, -double.MaxValue), 1);
extremeTree.Insert(new Rectangle(double.MaxValue, double.MaxValue, double.MaxValue, double.MaxValue), 2);
Check(extremeTree.Search(new Rectangle(double.MaxValue, double.MaxValue, double.MaxValue, double.MaxValue)).Single() == 2,
    "Extreme finite coordinates.");

SnapshotRTree<int> concurrent = new();
SpatialEntry<int>[] snapshotA = Enumerable.Range(0, 1_000)
    .Select(_ => new SpatialEntry<int>(new Rectangle(0, 0, 1, 1), 0)).ToArray();
SpatialEntry<int>[] snapshotB = Enumerable.Range(0, 1_000)
    .Select(_ => new SpatialEntry<int>(new Rectangle(100, 100, 101, 101), 1)).ToArray();
concurrent.ReplaceAll(snapshotA);
Check(concurrent.Count == 1_000, "Published count.");
try { concurrent.ReplaceAll(null!); throw new Exception("Null replacement accepted."); }
catch (ArgumentNullException) { }
Check(concurrent.Count == 1_000, "Failed replacement must preserve the previous tree.");
using ManualResetEventSlim start = new(false);
Task writer = Task.Run(() =>
{
    start.Wait();
    for (int i = 0; i < 100; i++) concurrent.ReplaceAll(i % 2 == 0 ? snapshotB : snapshotA);
});
Task[] readers = Enumerable.Range(0, 4).Select(_ => Task.Run(() =>
{
    List<int> found = [];
    start.Wait();
    for (int i = 0; i < 2_500; i++)
    {
        found.Clear();
        int count = concurrent.Search(new Rectangle(-1, -1, 102, 102), found);
        Check(count == 1_000 && found.Count == 1_000, "Concurrent snapshot count.");
        int version = found[0];
        Check(found.All(value => value == version), "Search observed a partial replacement.");
    }
})).ToArray();
start.Set();
Task.WaitAll([writer, .. readers]);
concurrent.ReplaceAll([]);
Check(concurrent.Count == 0 && concurrent.Search(new Rectangle(-1, -1, 102, 102)).Count == 0,
    "Empty replacement.");

using ConcurrentRTree<int> immediate = new();
SpatialEntry<int>[] movingBatch = Enumerable.Range(0, 1_000)
    .Select(i => new SpatialEntry<int>(new Rectangle(i, 0, i + 1, 1), i)).ToArray();
immediate.BulkLoad(movingBatch);
Check(immediate.Count == 1_000 && immediate.Search(new Rectangle(-1, -1, 1_001, 101)).Count == 1_000,
    "Initial mutable bulk load.");
Check(!immediate.Add(new Rectangle(0, 0, 1, 1), 0), "Duplicate mutable value accepted.");
Check(immediate.Move(0, new Rectangle(100, 100, 101, 101)), "Move mutable entry.");
Check(!immediate.Search(new Rectangle(0, 0, 0, 0)).Contains(0) &&
    immediate.Search(new Rectangle(100, 100, 101, 101)).Contains(0), "Moved bounds visible.");
Check(immediate.Remove(0) && !immediate.Remove(0), "Remove mutable entry.");
Check(immediate.Add(new Rectangle(0, 0, 1, 1), 0), "Re-add mutable entry.");
using ManualResetEventSlim mutableStart = new(false);
Task movingWriter = Task.Run(() =>
{
    mutableStart.Wait();
    for (int i = 0; i < 2_000; i++)
    {
        int id = i % 1_000;
        Rectangle next = (i / 1_000) % 2 == 0
            ? new Rectangle(id, 100, id + 1, 101)
            : new Rectangle(id, 0, id + 1, 1);
        Check(immediate.Move(id, next), "Concurrent mutable move.");
    }
});
Task[] movingReaders = Enumerable.Range(0, 4).Select(_ => Task.Run(() =>
{
    List<int> found = [];
    mutableStart.Wait();
    for (int i = 0; i < 1_000; i++)
    {
        found.Clear();
        Check(immediate.Search(new Rectangle(-1, -1, 1_001, 101), found) == 1_000 &&
            found.Distinct().Count() == 1_000, "Concurrent mutable search observed invalid entries.");
    }
})).ToArray();
mutableStart.Set();
Task.WaitAll([movingWriter, .. movingReaders]);
Check(immediate.Search(new Rectangle(-1, 0, 1_001, 1)).Order().SequenceEqual(Enumerable.Range(0, 1_000)) &&
    immediate.Search(new Rectangle(-1, 100, 1_001, 101)).Count == 0, "Moved entries returned to original bounds.");
immediate.Clear();
Check(immediate.Count == 0, "Mutable clear.");

Random movingRandom = new(73211);
SpatialEntry<int>[] frameA = new SpatialEntry<int>[10_000];
SpatialEntry<int>[] frameB = new SpatialEntry<int>[10_000];
for (int i = 0; i < frameA.Length; i++)
{
    Rectangle original = RandomRectangle(movingRandom);
    Rectangle shifted = new(original.MinX + 50, original.MinY + 50, original.MaxX + 50, original.MaxY + 50);
    frameA[i] = new SpatialEntry<int>(original, i);
    frameB[i] = new SpatialEntry<int>(shifted, i);
}
SnapshotRTree<int> frameSnapshot = new();
using ConcurrentRTree<int> frameMutable = new();
frameSnapshot.ReplaceAll(frameA);
frameMutable.BulkLoad(frameA);
for (int frame = 0; frame < 3; frame++)
{
    SpatialEntry<int>[] next = frame % 2 == 0 ? frameB : frameA;
    frameSnapshot.ReplaceAll(next);
    foreach (SpatialEntry<int> entry in next)
        Check(frameMutable.Move(entry.Item, entry.Bounds), "Frame move.");
    for (int q = 0; q < 100; q++)
    {
        Rectangle query = RandomRectangle(movingRandom);
        Check(frameSnapshot.Search(query).Order().SequenceEqual(frameMutable.Search(query).Order()),
            $"Frame differential: frame={frame}, query={q}.");
    }
}

GenericTests.Run();
Console.WriteLine("All R-tree differential and boundary checks passed.");
