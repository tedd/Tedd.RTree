"""Integrate the measured matched-subtree traversal; coordinate-independent comparisons."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
candidate = (RUN / 'MatchedContainedSpanRTree.cs').read_text()
start = candidate.index('    private static int CollectValues(')
end = candidate.index('    private bool Remove(', start)
body = candidate[start:end]
body = body.replace('        Span<Entry> entries = node.Entries.AsSpan(0, node.Count);',
'''        // Validate the active prefix once; mutations cannot overlap a search (H-004/H-014).
        Span<Entry> entries = node.Entries.AsSpan(0, node.Count);''')
body = body.replace('                if (entry.Bounds.Intersects(bounds))\n                    found += bounds.Contains(entry.Bounds) ? CollectValues(entry.Child!, results) : Search(entry.Child!, bounds, results);',
'''                if (entry.Bounds.Intersects(bounds))
                {
                    // Every descendant lies within this entry. Containment therefore permits
                    // collecting values without further geometry tests, preserving duplicates.
                    // Check only intersecting children to limit selective-query overhead (H-013/H-014).
                    found += bounds.Contains(entry.Bounds)
                        ? CollectValues(entry.Child!, results)
                        : Search(entry.Child!, bounds, results);
                }''')
for filename, bounds in (('RTree.cs', 'Rectangle'), ('RTree2D.Generic.cs', 'Rectangle2D<TCoordinate>'), ('RTree3D.Generic.cs', 'Box<TCoordinate>')):
    path = ROOT / 'src/Tedd.RTree' / filename
    source = path.read_text(encoding='utf-8-sig')
    begin = source.index('    private static int Search(')
    finish = source.index('    private bool Remove(', begin)
    replacement = body.replace('in Rectangle bounds', 'in ' + bounds + ' bounds')
    path.write_text(source[:begin] + replacement + source[finish:], encoding='utf-8')
