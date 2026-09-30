"""Preserve distinct follow-up mechanisms; called after initial confirmation."""
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
source = (RUN / 'MatchedContainedSpanRTree.cs').read_text()
start = source.index('    private static int Search(')
end = source.index('    private bool Remove(', start)
search = source[start:end]
counted = search.replace('                    found++;', '                    // Count from the appended list prefix instead.').replace(
    '        if (node.Leaf)\n        {', '        if (node.Leaf)\n        {\n            int before = results.Count;').replace(
    '        }\n        else', '            found = results.Count - before;\n        }\n        else')
count_source = source[:start] + counted + source[end:]
(RUN / 'ListCountRTree.cs').write_text(count_source.replace('MatchedContainedSpanRTree', 'ListCountRTree'))
start = source.index('    private static int CollectValues(')
end = source.index('    private static int Search(', start)
collector = source[start:end].replace('        if (node.Leaf)', '        Span<Entry> entries = node.Entries.AsSpan(0, node.Count);\n        if (node.Leaf)').replace('i < node.Count', 'i < entries.Length').replace('node.Entries[i]', 'entries[i]')
(RUN / 'SpanCollectorRTree.cs').write_text((source[:start] + collector + source[end:]).replace('MatchedContainedSpanRTree', 'SpanCollectorRTree'))

for dimension in ('2D', '3D'):
    source = (ROOT / 'src/Tedd.RTree' / ('RTree' + dimension + '.Generic.cs')).read_text()
    # Locals preserve original array indexing, while hoisting stable storage/count loads.
    start = source.index('    private static int Search(')
    end = source.index('    private bool Remove(', start)
    body = source[start:end].replace('Span<Entry> entries = node.Entries.AsSpan(0, node.Count);',
        'Entry[] entries = node.Entries;\n        int entryCount = node.Count;').replace('i < entries.Length', 'i < entryCount')
    source = source[:start] + body + source[end:]
    name = 'LocalArrayRTree' + dimension
    source = source.replace('RTree' + dimension + '<', name + '<').replace('public RTree' + dimension + '(', 'public ' + name + '(')
    (RUN / (name + '.cs')).write_text(source)

registration = (RUN / 'VariantRegistration.cs').read_text()
for name in ('ListCount', 'SpanCollector'):
    registration = registration.replace('    internal static void Initialize()\n    {',
        '    internal static void Initialize()\n    {\n' +
        f'        Screening.Variants["{name}"] = entries => {{ var tree = new {name}RTree<int>(); tree.BulkLoad(entries); return tree.Search; }};')
(RUN / 'VariantRegistration.cs').write_text(registration)
