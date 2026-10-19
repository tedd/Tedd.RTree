"""Verify and preserve task-owned evidence before workspace cleanup."""
from pathlib import Path
import hashlib,json,zipfile

REPO=Path(__file__).resolve().parents[2]
ROOT=Path('D:/Workspaces/AI/rtree-specialization-20261019')
OUTPUT=REPO/'Research/2026-10-19-specialization/reproduction.zip'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    assert ROOT.resolve()==Path('D:/Workspaces/AI/rtree-specialization-20261019').resolve()
    files=set()
    for name in ('library-source','epoch1-source','epoch2-source','epoch4-source','proposal-source','boundary-source','contracts-source'):
        files.update(p for p in (ROOT/name).rglob('*') if p.is_file() and p.suffix in ('.cs','.csproj') and not {'obj','bin'}.intersection(p.parts))
    for name in ('library','caller','epoch1-caller','epoch2-caller','epoch3-caller','epoch4-caller','tests','proposal-library','proposal-caller','proposal-tests','comparison-caller','comparison-libraries','boundary-library','boundary-caller','contracts-library','contracts-tests'):
        files.update(p for p in (ROOT/name).glob('*') if p.is_file() and p.suffix in ('.dll','.pdb','.json'))
    files.update(p for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.cs','.csproj','.json','.txt','.out','.err'))
    files.update((ROOT/'comparison-packages').glob('*.nupkg'))
    retained=ROOT/'retained'
    files.update(retained.glob('fixture-*.txt'))
    files.update(retained/name for name in ('static.zip','geo.zip','global.json'))
    native=retained/'native'
    files.update(native/name for name in ('Cargo.lock','Cargo.toml','src/lib.rs','src/main.rs','target/release/packed-worker.exe','target/release/packed_native.dll'))
    files=sorted(p for p in files if p.is_file())
    manifest={}
    with zipfile.ZipFile(OUTPUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            name=p.relative_to(ROOT).as_posix();data=p.read_bytes()
            manifest[name]=dict(sha256=sha(data),bytes=len(data));z.writestr(name,data)
    bindings={}
    for folder in (REPO/'benchmarks/specialization',OUTPUT.parent,REPO/'benchmarks/results/specialization'):
        for p in folder.rglob('*'):
            if p.is_file() and p not in (OUTPUT,OUTPUT.with_suffix('.manifest.json')):
                bindings[p.relative_to(REPO).as_posix()]=sha(p.read_bytes())
    record=dict(archive_sha256=sha(OUTPUT.read_bytes()),prior_archive_sha256=sha((REPO/'Research/2026-10-18-simd/reproduction.zip').read_bytes()),files=manifest,repository_evidence=bindings,
        exclusions='No policy/signing files, catalogs, credentials, compiler caches or unrelated workspaces. Exported capture/request/grant records remain in repository evidence.')
    OUTPUT.with_suffix('.manifest.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        assert all(sha(z.read(n))==v['sha256'] for n,v in manifest.items())
    print(f'Verified {len(files)} archived files, {OUTPUT.stat().st_size} bytes; {len(bindings)} repository evidence hashes.')

if __name__=='__main__':main()
