"""Create independently compiled candidate trees from the preserved baseline."""
from pathlib import Path

RUN = Path(__file__).resolve().parent
BASE = (RUN / 'BaselineRTree.cs').read_text(encoding='utf-8-sig')

collect = '''    private static int CollectValues(Node node, List<T> results)
    {
        if (node.Leaf)
        {
            for (int i = 0; i < node.Count; i++) results.Add(node.Entries[i].Value);
            return node.Count;
        }
        int found = 0;
        for (int i = 0; i < node.Count; i++) found += CollectValues(node.Entries[i].Child!, results);
        return found;
    }

'''
search_start = '    private static int Search(Node node, in Rectangle bounds, List<T> results)\n    {\n'

def contains(source, condition):
    return source.replace(search_start, collect + search_start +
        f'        if ({condition}) return CollectValues(node, results);\n')

def span(source):
    start = source.index(search_start)
    end = source.index('    private bool Remove(', start)
    body = source[start:end].replace('        int found = 0;',
        '        Span<Entry> entries = node.Entries.AsSpan(0, node.Count);\n        int found = 0;')
    body = body.replace('i < node.Count', 'i < entries.Length').replace('ref node.Entries[i]', 'ref entries[i]')
    return source[:start] + body + source[end:]

sources = {
    'Contained': contains(BASE, 'bounds.Contains(node.Bounds)'),
    'InternalContained': contains(BASE, '!node.Leaf && bounds.Contains(node.Bounds)'),
    'RootContained': BASE.replace('        return Search(_root, bounds, results);',
        '        if (bounds.Contains(_root.Bounds)) return CollectValues(_root, results);\n        return Search(_root, bounds, results);')
        .replace(search_start, collect + search_start),
    'SpanTraversal': span(BASE),
    'ContainedSpan': span(contains(BASE, 'bounds.Contains(node.Bounds)')),
    'CachedAreas': BASE.replace('        double worstWaste = double.NegativeInfinity;',
        '        Span<double> areas = stackalloc double[length];\n        for (int i = 0; i < length; i++) areas[i] = entries[i].Bounds.Area;\n        double worstWaste = double.NegativeInfinity;')
        .replace('entries[i].Bounds.Area - entries[j].Bounds.Area;', 'areas[i] - areas[j];'),
    'StackAssigned': BASE.replace('        bool[] assigned = new bool[length];',
        '        Span<bool> assigned = stackalloc bool[length];\n        assigned.Clear();'),
}
sources['MatchedContained'] = BASE.replace(search_start, collect + search_start).replace(
    '                    found += Search(entry.Child!, bounds, results);',
    '                    found += bounds.Contains(entry.Bounds) ? CollectValues(entry.Child!, results) : Search(entry.Child!, bounds, results);')
sources['MatchedContainedSpan'] = span(sources['MatchedContained'])
sources['InternalContainedSpan'] = span(sources['InternalContained'])
for name in ('MatchedContained', 'MatchedContainedSpan'):
    sources[name + 'Point'] = sources[name].replace(
        '        return Search(_root, bounds, results);',
        '        return bounds.MinX == bounds.MaxX || bounds.MinY == bounds.MaxY ? SearchSelective(_root, bounds, results) : Search(_root, bounds, results);')
    start = BASE.index(search_start)
    end = BASE.index('    private bool Remove(', start)
    selective = BASE[start:end].replace('Search(', 'SearchSelective(')
    sources[name + 'Point'] = sources[name + 'Point'].replace(search_start, selective + search_start)

# A distinct algorithm: normalized separation seeds, then one pass assigning entries.
linear = BASE
start = linear.index('        double worstWaste = double.NegativeInfinity;')
end = linear.index('        Node other =', start)
linear = linear[:start] + '''        double bestSeparation = double.NegativeInfinity;
        for (int axis = 0; axis < 2; axis++)
        {
            int highLow = 0, lowHigh = 0;
            double minimum = double.PositiveInfinity, maximum = double.NegativeInfinity;
            for (int i = 0; i < length; i++)
            {
                Rectangle b = entries[i].Bounds;
                double low = axis == 0 ? b.MinX : b.MinY, high = axis == 0 ? b.MaxX : b.MaxY;
                double highestLow = axis == 0 ? entries[highLow].Bounds.MinX : entries[highLow].Bounds.MinY;
                double lowestHigh = axis == 0 ? entries[lowHigh].Bounds.MaxX : entries[lowHigh].Bounds.MaxY;
                if (low > highestLow) highLow = i;
                if (high < lowestHigh) lowHigh = i;
                minimum = Math.Min(minimum, low);
                maximum = Math.Max(maximum, high);
            }
            double separation = ((axis == 0 ? entries[highLow].Bounds.MinX : entries[highLow].Bounds.MinY) -
                (axis == 0 ? entries[lowHigh].Bounds.MaxX : entries[lowHigh].Bounds.MaxY)) / (maximum - minimum);
            if (highLow != lowHigh && separation > bestSeparation)
            {
                seedA = highLow; seedB = lowHigh; bestSeparation = separation;
            }
        }

''' + linear[end:]
start = linear.index('            double greatestDifference =')
end = linear.index('            Node destination =', start)
linear = linear[:start] + '''            double enlargementA = 0, enlargementB = 0;
            for (int i = 0; i < length; i++)
            {
                if (assigned[i]) continue;
                selected = i;
                enlargementA = Enlargement(node.Bounds, entries[i].Bounds);
                enlargementB = Enlargement(other.Bounds, entries[i].Bounds);
                break;
            }

''' + linear[end:]
# Scanning the assignment flags from the beginning would still be quadratic.
linear = linear.replace('        while (remaining > 0)', '        int cursor = 0;\n        while (remaining > 0)')
linear = linear.replace('for (int i = 0; i < length; i++)\n            {\n                if (assigned[i]) continue;',
    'for (int i = cursor; i < length; i++)\n            {\n                if (assigned[i]) continue;\n                cursor = i + 1;')
sources['LinearSplit'] = linear

for name, source in sources.items():
    source = source.replace('BaselineRTree', name + 'RTree')
    (RUN / (name + 'RTree.cs')).write_text(source, encoding='utf-8')

registration = '''using Tedd.RTree;
internal static class VariantRegistration
{
    [System.Runtime.CompilerServices.ModuleInitializer]
    internal static void Initialize()
    {
'''
for name in ('Contained', 'InternalContained', 'RootContained', 'SpanTraversal', 'ContainedSpan',
             'MatchedContained', 'MatchedContainedSpan', 'InternalContainedSpan', 'MatchedContainedPoint', 'MatchedContainedSpanPoint'):
    registration += f'        Screening.Variants["{name}"] = entries => {{ var tree = new {name}RTree<int>(); tree.BulkLoad(entries); return tree.Search; }};\n'
for capacity in (8, 32, 64):
    registration += f'        Screening.Variants["Capacity{capacity}"] = entries => {{ var tree = new BaselineRTree<int>({capacity}); tree.BulkLoad(entries); return tree.Search; }};\n'
registration += '    }\n}\n'
(RUN / 'VariantRegistration.cs').write_text(registration, encoding='utf-8')
