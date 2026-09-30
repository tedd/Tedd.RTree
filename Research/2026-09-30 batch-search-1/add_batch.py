"""Apply the same batch query contract to all coordinate and concurrency variants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/Tedd.RTree'
for suffix, bounds in (('', 'Rectangle'), ('2D.Generic', 'Rectangle2D<TCoordinate>'), ('3D.Generic', 'Box<TCoordinate>')):
    for family in ('RTree', 'ConcurrentRTree', 'SnapshotRTree'):
        filename = family + ('.cs' if not suffix else suffix + '.cs')
        path = SRC / filename
        source = path.read_text(encoding='utf-8-sig')
        marker = '    /// <summary>Returns '
        start = source.index(marker, source.index('    public int Search('))
        docs = '''    /// <summary>Appends matches for each query to its result list and writes the appended counts.</summary>
    /// <returns>The total number of matches appended across all queries.</returns>
    /// <remarks>
    /// Results must have one non-null list per query; counts must have at least one slot per query.
    /// Existing list contents are preserved. Inputs and output storage must not be changed concurrently.
'''
        if family == 'ConcurrentRTree':
            docs += '    /// The whole batch holds one read lock, so writers wait until the batch completes.\n'
        elif family == 'SnapshotRTree':
            docs += '    /// All queries use one published version, including during concurrent replacements.\n'
        else:
            docs += '    /// The tree must not be mutated while the batch runs.\n'
        docs += f'''    /// </remarks>
    public long SearchBatch(ReadOnlySpan<{bounds}> queries, ReadOnlySpan<List<T>> results, Span<int> counts)
'''
        if family == 'RTree':
            body = '''    {
        if (results.Length != queries.Length)
            throw new ArgumentException("Provide one result list per query.", nameof(results));
        if (counts.Length < queries.Length)
            throw new ArgumentException("Provide at least one count slot per query.", nameof(counts));
        // Validate the entire batch before appending, including lists belonging to empty queries.
        for (int i = 0; i < results.Length; i++)
            if (results[i] is null)
                throw new ArgumentException("Result lists must not be null.", nameof(results));
        long total = 0;
        for (int i = 0; i < queries.Length; i++)
        {
            int found = Search(queries[i], results[i]);
            counts[i] = found;
            total += found;
        }
        return total;
    }

'''
        elif family == 'ConcurrentRTree':
            body = '''    {
        _lock.EnterReadLock();
        try { return _tree.SearchBatch(queries, results, counts); }
        finally { _lock.ExitReadLock(); }
    }

'''
        else:
            body = '        => Volatile.Read(ref _current).SearchBatch(queries, results, counts);\n\n'
        path.write_text(source[:start] + docs + body + source[start:], encoding='utf-8')
