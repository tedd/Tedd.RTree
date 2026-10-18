"""Preserve task-owned, non-secret experimental inputs before scratch cleanup."""
from pathlib import Path
import hashlib
import json
import zipfile
import difflib

ROOT = Path('D:/Workspaces/AI/rtree-simd-20261018')
REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO/'Research/2026-10-18-simd/reproduction.zip'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def preserve():
    for stage in ('selected','keyvector'):
        patch=[]
        control=ROOT/'baseline-source/src/Tedd.RTree'
        treatment=ROOT/f'{stage}-source/src/Tedd.RTree'
        for source in sorted(control.glob('*.cs')):
            patch.extend(difflib.unified_diff(source.read_text().splitlines(keepends=True),
                (treatment/source.name).read_text().splitlines(keepends=True),
                fromfile=f'a/src/Tedd.RTree/{source.name}',tofile=f'b/src/Tedd.RTree/{source.name}'))
        (OUTPUT.parent/f'{stage}.patch').write_text(''.join(patch),encoding='utf8',newline='\n')
    files = set()
    for directory in ROOT.glob('*-source'):
        files.update(p for p in directory.rglob('*') if p.suffix in ('.cs', '.csproj') and 'obj' not in p.parts)
    for pattern in ('*-library', '*-worker', '*-warm-worker', 'caller', 'file-caller', 'warm-caller'):
        for directory in ROOT.glob(pattern):
            files.update(p for p in directory.iterdir() if p.suffix in ('.dll', '.pdb', '.json'))
    for pattern in ('fixture-*.txt', '*-tests-*.log', '*-build.log', '*-codegen.log', 'starting-source.json',
                    'global.json', 'WarmWorker.cs', 'Warm.csproj', 'static.zip', 'geo.zip'):
        files.update(ROOT.glob(pattern))
    native = ROOT/'native'
    files.update(native/name for name in ('Cargo.lock','Cargo.toml','src/lib.rs','src/bin/packed-worker.rs') if (native/name).is_file())
    files.update((native/'src').rglob('*.rs'))
    files.update((native/'target/release')/name for name in ('packed-worker.exe','packed_native.dll'))
    files = sorted(p for p in files if p.is_file())
    manifest = {}
    # Deliberately exclude catalogs, policy/signing files, caches and environment.
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest[name] = dict(sha256=digest(data), bytes=len(data))
            archive.writestr(name, data)
    manifest_path = OUTPUT.with_suffix('.manifest.json')
    manifest_path.write_text(json.dumps(dict(archive_sha256=digest(OUTPUT.read_bytes()), files=manifest),indent=2))
    with zipfile.ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None: raise RuntimeError('Archive CRC failure')
        for name, identity in manifest.items():
            if digest(archive.read(name)) != identity['sha256']: raise RuntimeError('Archive content drift')
    print(f'Preserved and verified {len(files)} files; {OUTPUT.stat().st_size} compressed bytes.')

if __name__ == '__main__':
    preserve()
