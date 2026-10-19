"""Verify complete observations and preserve owned artifacts before workspace removal."""
import sys
sys.dont_write_bytecode=True
import csv,hashlib,json,zipfile
from pathlib import Path
import study as r

EXPECTED={'construction':90,'traversal':72,'remedies':90,'query-remedies':126,'passes':90,'representation':72,
          'confirmation':90,'tiered':72,'fallback':36,'boundary':24,'confirmation-2':90,'tiered-2':72,'fallback-2':36,
          'jit-policy':30,'confirmation-3':90,'tiered-3':72,'fallback-3':36,'comparison':234}

def audit():
    phases=[]
    for phase,count in EXPECTED.items():
        dest=r.EVIDENCE/phase;protocol=json.loads((dest/'protocol.json').read_text());samples=json.loads((dest/'samples.json').read_text());launches=json.loads((dest/'launches.json').read_text())
        assert len(protocol['jobs'])==count and len(launches)==count and len(list(dest.glob('*.out')))==count
        recovered=[]
        for i,launch in enumerate(launches):
            out,err=(dest/f'{i:03d}.out').read_text().split('\nSTDERR:\n',1)
            expected=128 if launch['mode'].startswith('mutable') and phase!='comparison' else 64
            assert f'validated={expected}' in err
            for op,us,reps,alloc in csv.reader(out.strip().splitlines()):
                recovered.append(dict(block=launch['block'],size=launch['size'],distribution=launch['distribution'],mode=launch['mode'],operation=op,
                    us=float(us),repetitions=int(reps),allocated=float(alloc) if alloc!='NA' else None))
        assert recovered==samples,('Raw/summary mismatch',phase)
        missing=[i for i,v in enumerate(launches) if v.get('pid') is None]
        assert missing==([111] if phase=='query-remedies' else [])
        phases.append(dict(phase=phase,processes=count,observations=len(samples),missing_pid_indices=missing,protocol=r.sha(dest/'protocol.json')))
    original=json.loads((r.REPORT/'final-selection.json').read_text())['original_production']
    plan=json.loads((r.REPORT/'integration-plan.json').read_text())
    applied=all((r.REPO/v['path']).exists() and r.sha(r.REPO/v['path'])==v['after_sha256'] for v in plan)
    if not applied:assert all(r.sha(r.REPO/'src/Tedd.RTree'/name)==digest for name,digest in original.items())
    result=dict(processes=sum(EXPECTED.values()),phases=phases,applied=applied,
        caveat='One exploratory raw observation lacks PID/start bookkeeping after its recorded summary-write failure. No completed observation was replaced. Process blocks do not establish independence or statistical significance.')
    r.atomic_json(r.REPORT/'audit.json',result)
    print('Verified',result['processes'],'scheduled processes and all raw observations.')

def archive():
    audit();root=r.ROOT.resolve();assert root==Path('D:/Workspaces/AI/rtree-binary-20261019').resolve()
    files=set()
    for name in ('proposal-source','source','final-source','baseline-source','boundary-final-source','vector-final-source','prepolicy-final-source','private-opt-source','public-opt-source','review-source','integration'):
        files.update(p for p in (root/name).rglob('*') if p.is_file() and p.suffix in ('.cs','.csproj','.md') and not {'obj','bin'}.intersection(p.parts))
    for folder in root.iterdir():
        if folder.is_dir() and (folder.name.endswith(('-library','-caller','-tests')) or folder.name in ('construction-caller','tests','comparison-libraries','integrated-library','integrated-caller','integrated-tests','verify-il')):
            files.update(p for p in folder.glob('*') if p.is_file() and p.suffix in ('.dll','.pdb','.json','.xml'))
    files.update(p for p in root.iterdir() if p.is_file() and p.suffix in ('.cs','.csproj','.txt','.json','.jsonl','.out','.err'))
    files.update((root/'retained').glob('fixture-*.txt'))
    files.update(root/'retained'/n for n in ('static.zip','geo.zip','global.json','native/Cargo.toml','native/Cargo.lock','native/src/lib.rs','native/src/main.rs','native/target/release/packed-worker.exe','native/target/release/packed_native.dll'))
    files=sorted(p for p in files if p.is_file())
    output=r.REPORT/'reproduction.zip';manifest={}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            name=p.relative_to(root).as_posix();data=p.read_bytes();manifest[name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data));z.writestr(name,data)
    # Every hash-bound library source can be located in the retained source versions.
    bindings={}
    for phase in EXPECTED:
        protocol=json.loads((r.EVIDENCE/phase/'protocol.json').read_text())
        sources={k:v for k,v in protocol.items() if k in ('source','selected_source','boundary_source') and isinstance(v,dict)}
        sources.update(protocol.get('sources',{}))
        for label,items in sources.items():
            if not items or not all(isinstance(v,str) for v in items.values()):continue
            matched={}
            for name,digest in items.items():
                options=[n for n,v in manifest.items() if Path(n).name==name and v['sha256']==digest]
                assert options,('Missing bound source',phase,label,name,digest)
                matched[name]=options[0]
            bindings[phase+'/'+label]=matched
    repository={}
    for folder in (r.REPORT,r.EVIDENCE,r.REPO/'benchmarks/binary-packed'):
        for p in folder.rglob('*'):
            if p.is_file() and p not in (output,output.with_suffix('.manifest.json')):
                repository[p.relative_to(r.REPO).as_posix()]=r.sha(p)
    record=dict(archive_sha256=r.sha(output),files=manifest,epoch_source_bindings=bindings,repository_evidence=repository,
        exclusions='No signing/policy files, credentials, private catalogs, compiler caches or unrelated workspaces. Exported diagnostics remain in repository evidence.')
    r.atomic_json(output.with_suffix('.manifest.json'),record)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None and all(hashlib.sha256(z.read(n)).hexdigest()==v['sha256'] for n,v in manifest.items())
    print('Verified archive:',len(files),'files,',output.stat().st_size,'bytes.')

if __name__=='__main__':
    if sys.argv[1]=='audit':audit()
    elif sys.argv[1]=='archive':archive()
    else:raise ValueError(sys.argv[1])
