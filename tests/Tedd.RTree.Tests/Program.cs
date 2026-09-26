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
}

RTree<int> extremeTree = new(4);
extremeTree.Insert(new Rectangle(-double.MaxValue, -double.MaxValue, -double.MaxValue, -double.MaxValue), 1);
extremeTree.Insert(new Rectangle(double.MaxValue, double.MaxValue, double.MaxValue, double.MaxValue), 2);
Check(extremeTree.Search(new Rectangle(double.MaxValue, double.MaxValue, double.MaxValue, double.MaxValue)).Single() == 2,
    "Extreme finite coordinates.");

Console.WriteLine("All R-tree differential and boundary checks passed.");
