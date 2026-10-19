"""Prepare/apply a hash-bound local source patch; never deploys or accesses services."""
import sys
sys.dont_write_bytecode=True
import difflib,json
from pathlib import Path
import study as r

PLAN=r.REPORT/'integration-plan.json'

def prepare():
    source=r.ROOT/'final-source/src/Tedd.RTree';changes={}
    selection=json.loads((r.REPORT/'final-selection.json').read_text())
    for name,digest in selection['original_production'].items():assert r.sha(r.REPO/'src/Tedd.RTree'/name)==digest
    for suffix,kind,bounds in (('', 'RTree<T>', 'Rectangle'),('2D.Generic','RTree2D<TCoordinate, T>','Rectangle2D<TCoordinate>'),('3D.Generic','RTree3D<TCoordinate, T>','Box<TCoordinate>')):
        for prefix in ('','Snapshot','Concurrent'):
            path=r.REPO/f'src/Tedd.RTree/{prefix}RTree{suffix}.cs';before=path.read_bytes()
            decl='public sealed class '+prefix+kind
            contract=('IMutableSpatialIndex' if not prefix else 'IReadOnlySpatialIndex')+f'<{bounds}, T>'
            old=decl+(' : IDisposable' if prefix=='Concurrent' else '')
            new=decl+(' : IDisposable, ' if prefix=='Concurrent' else ' : ')+contract
            assert before.count(old.encode())==1
            changes[path.relative_to(r.REPO).as_posix()]=before.replace(old.encode(),new.encode(),1)
    for name in ('IReadOnlySpatialIndex.cs','PackedRTree.cs','PackedKeyEncoding.cs','PackedHilbertOrder.cs'):
        path=r.REPO/'src/Tedd.RTree'/name;assert not path.exists()
        changes[path.relative_to(r.REPO).as_posix()]=(source/name).read_bytes()
    changes['tests/Tedd.RTree.Tests/PackedRTreeChecks.cs']=(r.REPORT/'PackedRTreeChecks.cs').read_bytes()
    path=r.REPO/'tests/Tedd.RTree.Tests/Program.cs';before=path.read_bytes();eol=b'\r\n' if b'\r\n' in before else b'\n'
    changes[path.relative_to(r.REPO).as_posix()]=before.replace(b'MutablePackedChecks.Run();',b'PackedRTreeChecks.Run();'+eol+b'MutablePackedChecks.Run();',1)
    path=r.REPO/'src/Tedd.RTree/Tedd.RTree.csproj';before=path.read_bytes()
    changes[path.relative_to(r.REPO).as_posix()]=before.replace(b'Highly optimized mutable 2D and 3D R-trees for .NET 10.',b'Mutable 2D and 3D R-trees and an immutable packed 2D index for .NET 10.',1)
    path=r.REPO/'README.md';before=path.read_bytes();eol='\r\n' if b'\r\n' in before else '\n';text=before.decode().replace('\r\n','\n')
    text=text.replace('A mutable 2D and 3D R-tree library for .NET 10.','A .NET 10 spatial index library with mutable 2D and 3D R-trees and an immutable packed 2D index.',1)
    text=text.replace('The tree uses Sort-Tile-Recursive bulk packing,','The 2D trees use Hilbert ordering for bulk packing,',1)
    section='''## Immutable indexes

Use `PackedRTree<T>` for a batch of 2D `Rectangle` bounds that remains unchanged. Its constructor copies entries into owned storage. Input arrays and an optional `BulkLoadWorkspace` can be reused after construction. Concurrent searches require separate result lists.

```csharp
SpatialEntry<string>[] entries =
[
    new(new Rectangle(0, 0, 10, 10), "A"),
    new(new Rectangle(20, 20, 30, 30), "B")
];
IReadOnlySpatialIndex<Rectangle, string> index = new PackedRTree<string>(entries);
List<string> matches = index.Search(new Rectangle(5, 5, 25, 25));
```

`IReadOnlySpatialIndex<TBounds, T>` shares `Count`, `Search`, and `SearchBatch` across the packed, mutable, snapshot, and concurrent indexes. `IMutableSpatialIndex<TBounds, T>` adds `Insert`, `Remove`, `Update`, and `Clear` on the plain mutable trees. A read-only interface does not make a mutable implementation immutable or synchronize access. Use `RTree<T>` for individual changes; use the coordinate-generic trees for other coordinate types or 3D bounds.

'''
    text=text.replace('## Batch searches\n',section+'## Batch searches\n',1)
    changes['README.md']=text.replace('\n',eol).encode()
    plan=[];patch=[];staged=r.ROOT/'integration';staged.mkdir(exist_ok=True)
    for name,after in sorted(changes.items()):
        path=r.REPO/name;before=path.read_bytes() if path.exists() else b''
        dest=staged/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(after)
        plan.append(dict(path=name,before_sha256=r.sha(path) if path.exists() else None,after_sha256=r.sha(dest)))
        patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile='a/'+name if path.exists() else '/dev/null',tofile='b/'+name))
    r.atomic_json(PLAN,plan);(r.REPORT/'implementation.patch').write_bytes(''.join(patch).encode())
    print('Reviewable patch:',len(plan),'files. Production source has not been changed.')

def gates():
    selection=json.loads((r.REPORT/'final-selection.json').read_text())
    suffix=selection.get('confirmation_suffix','-2' if 'NoInlining' in selection['selected'] else '')
    def table(phase):return {(v['size'],v['distribution'],v['mode'],v['operation']):v['median_us'] for v in json.loads((r.EVIDENCE/phase/'summary.json').read_text())}
    failure=[];t=table('confirmation'+suffix)
    for n in (1000,10000,100000):
        for d in ('uniform','clustered'):
            for op in ('build','queries'):
                ratio=t[n,d,'packed',op]/t[n,d,'control',op]
                if ratio>1.10:failure.append(('confirmation',n,d,op,ratio))
            if n==1000 and t[n,d,'packed','build']/t[n,d,'control','build']>.90:failure.append(('primary',n,d))
    t=table('tiered'+suffix)
    for n in (1000,10000,100000):
        for d in ('uniform','clustered'):
            for mode in ('control','mutable'):
                ratio=t[n,d,'packed','queries']/t[n,d,mode,'queries']
                if ratio>1.10:failure.append(('tiered',n,d,mode,ratio))
    t=table('fallback'+suffix)
    for n in (1000,10000,100000):
        for d in ('uniform','clustered'):
            ratio=t[n,d,'packed','queries']/t[n,d,'control','queries']
            if ratio>1.10:failure.append(('fallback',n,d,ratio))
    r.atomic_json(r.REPORT/'adoption-gates.json',dict(passed=not failure,failures=failure))
    if failure:raise RuntimeError(('Mandatory performance guard failed',failure))
    print('All prospective source-adoption guards pass.')

def apply():
    gates();plan=json.loads(PLAN.read_text())
    for change in plan:
        path=r.REPO/change['path'];current=r.sha(path) if path.exists() else None
        assert current==change['before_sha256'],('Preimage changed',str(path))
        assert r.sha(r.ROOT/'integration'/change['path'])==change['after_sha256']
    for change in plan:
        (r.REPO/change['path']).write_bytes((r.ROOT/'integration'/change['path']).read_bytes())
    print('Applied local implementation, contracts, tests and API documentation. No deployment or publication.')

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='gates':gates()
    elif sys.argv[1]=='apply':apply()
    else:raise ValueError(sys.argv[1])
