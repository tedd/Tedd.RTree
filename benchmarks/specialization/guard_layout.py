"""Isolate the caller-side recursion guard; leave the rejected implementation intact."""
from pathlib import Path
ROOT=Path('D:/Workspaces/AI/rtree-specialization-20261019')
REPO=Path(__file__).resolve().parents[2]
REPORT=REPO/'Research/2026-10-19-specialization'

def generate():
    source=ROOT/'library-source/src/Tedd.RTree'
    t=(REPORT/'PartialOrder.cs').read_text().replace('class PartialOrder','class GuardedOrder')
    marker='            Partition(keys, order, scratch, previous, next, shift - 8, capacity);'
    assert t.count(marker)==1
    t=t.replace(marker,'''            if (shift > 0 && next - previous > 1 && previous / capacity != (next - 1) / capacity)
                Partition(keys, order, scratch, previous, next, shift - 8, capacity);''')
    for name,text in [('GuardedOrder.cs',t),
        ('GuardPartitionRTree.cs',(source/'PartitionRTree.cs').read_text().replace('PartitionRTree<T>','GuardPartitionRTree<T>').replace('public PartitionRTree(','public GuardPartitionRTree(').replace('PartialOrder.Sort','GuardedOrder.Sort')),
        ('GuardPackedRTree.cs',(REPORT/'PackedRTree.cs').read_text().replace('PackedRTree<T>','GuardPackedRTree<T>').replace('public PackedRTree(','public GuardPackedRTree(').replace('PartialOrder.Sort','GuardedOrder.Sort'))]:
        (REPORT/name).write_text(text,encoding='utf8',newline='\n')
        (source/name).write_text(text,encoding='utf8',newline='\n')
    leaf=(REPORT/'ColumnPackedRTree.cs').read_text().replace('ColumnPackedRTree<T>','LeafColumnPackedRTree<T>').replace('public ColumnPackedRTree(','public LeafColumnPackedRTree(')
    leaf=leaf.replace('                    found += AppendMatch(level, index, bounds, results);',
        '                    if (level == 0) { results.Add(_values[index]); found++; }\n                    else found += AppendMatch(level, index, bounds, results);')
    leaf=leaf.replace('                found += AppendMatch(level, i, bounds, results);',
        '            {\n                if (level == 0) { results.Add(_values[i]); found++; }\n                else found += AppendMatch(level, i, bounds, results);\n            }')
    (REPORT/'LeafColumnPackedRTree.cs').write_text(leaf,encoding='utf8',newline='\n')
    (source/'LeafColumnPackedRTree.cs').write_text(leaf,encoding='utf8',newline='\n')
    t=(REPO/'benchmarks/specialization/Worker.cs').read_text()
    marker='    if (mode == "partition")'
    assert t.count(marker)==1
    t=t.replace(marker,'''    if (mode == "guard-mutable") { var t = new GuardPartitionRTree<int>(); t.BulkLoad(entries); return t; }
    if (mode == "guard-flat") return new GuardPackedRTree<int>(entries, partial: true);
    if (mode.StartsWith("leaf-")) return new LeafColumnPackedRTree<int>(entries, vectorWidth: int.Parse(mode[5..]));
'''+marker)
    t=t.replace('ResearchChecks.Run(); ExtraChecks.Run();','ResearchChecks.Run(); ExtraChecks.Run(); GuardChecks.Run();')
    (ROOT/'GuardWorker.cs').write_text(t,encoding='utf8',newline='\n')
    (REPORT/'guard-worker.cs.txt').write_text(t,encoding='utf8',newline='\n')
