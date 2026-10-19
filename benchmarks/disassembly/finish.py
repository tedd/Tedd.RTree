"""Audit all frozen observations and preserve reproduction before owned cleanup."""
import sys
sys.dont_write_bytecode=True
import hashlib
import json
import platform
import statistics
import winreg
import zipfile
import study as r

def audit():
    audits={}
    for phase,protocol_name,samples_name,count in (
        ('measurements','quiet-protocol.json','samples.json',108),
        ('refinement','refinement-protocol.json','refinement-samples.json',90)):
        protocol=json.loads((r.REPORT/protocol_name).read_text())
        samples=json.loads((r.REPORT/samples_name).read_text())
        assert len(protocol['jobs'])==count
        assert len(samples)==count*5
        for i,(block,n,dist,mode) in enumerate(protocol['jobs']):
            log=(r.REPORT/phase/f'{i:03d}.txt').read_text()
            assert 'validated=64' in log
            rows=[s for s in samples if (s['block'],s['size'],s['distribution'],s['mode'])==(block,n,dist,mode)]
            assert len(rows)==5
            assert {s['operation'] for s in rows}=={'build','query0','query1','query2','query3'}
            assert all(s['us']>0 and s['repetitions']>0 for s in rows)
        audits[phase]=dict(processes=count,raw_rows=len(samples),all_validated=True,discarded=0,replaced=0)
    r.save('audit.json',audits)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0]
    runtime=r.DOTNET.parent/'shared/Microsoft.NETCore.App/10.0.13'
    r.save('environment.json',dict(cpu=cpu,os=platform.platform(),architecture=platform.machine(),runtime='10.0.13',
        runtime_hashes={n:r.sha(runtime/n) for n in ('coreclr.dll','clrjit.dll','System.Private.CoreLib.dll')},
        observer_diagnostic='JitDisasm (managed); offline LLVM disassembly (native)',observer_quiet='none',
        uncontrolled='Desktop activity, CPU frequency and thermal state were not controlled; process blocks do not establish independence.'))
    dispositions={}
    sections=[]
    for label,name,candidate in (('First intervention','summary.json','leaf'),('Refinement','refinement-summary.json','tuned')):
        rows=json.loads((r.REPORT/name).read_text())
        t={(v['size'],v['distribution'],v['mode'],v['operation']):v['median_us'] for v in rows}
        primary=t[1000,'uniform',candidate,'queries']/t[1000,'uniform','list','queries']
        failures=[]
        for n in (1000,10000,100000):
            for dist in ('uniform','clustered'):
                for operation in ('build','queries'):
                    ratio=t[n,dist,candidate,operation]/t[n,dist,'list',operation]
                    if ratio>1.10:failures.append(dict(size=n,distribution=dist,operation=operation,ratio=ratio))
        dispositions[candidate]=dict(primary_ratio=primary,primary_passed=primary<=.90,
            guard_failures=failures,exploratory_gate_passed=primary<=.90 and not failures,
            independently_confirmed=False,adopted=False)
        sections += [f'## {label}', '', '| Entries | Distribution | List | SIMD consumer | AVX leaf + list | AVX leaf + SIMD | Rust |',
                     '|---:|---|---:|---:|---:|---:|---:|']
        combined='combined' if candidate=='leaf' else 'tuned-simd'
        for n in (1000,10000,100000):
            for dist in ('uniform','clustered'):
                values=[t[n,dist,m,'queries'] for m in ('list','simd',candidate,combined,'rust')]
                sections.append(f'| {n:,} | {dist} | '+' | '.join(f'{v:.3f}' for v in values)+' |')
        sections += ['',f'Library primary ratio: {primary:.6f}; guard failures: {len(failures)}.', '']
    r.save('dispositions.json',dispositions)
    (r.REPORT/'RESULTS.md').write_text('# Disassembly intervention results\n\nMedian microseconds for all 64 materialized-and-consumed query windows. All construction times, individual query groups, ranges, allocations and raw observations remain in the JSON/raw files. These are descriptive exploratory results, not a new complete competitor ranking. SIMD consumer changes affect caller work, not library work.\n\n'+'\n'.join(sections),encoding='utf8')
    print(json.dumps(dispositions,indent=2),flush=True)

def archive():
    archive=r.REPORT/'reproduction.zip'
    assert not archive.exists()
    prefixes=('retained/','comparison-caller/','final-caller/','library/','leaf-library/','tuned-library/',
              'leaf-source/','tuned-source/','tests/','leaf-tests/','tuned-tests/')
    callers={'caller-'+m for m in ('list','span','simd','leaf','combined','tuned','tuned-simd')}
    records={}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(r.ROOT.rglob('*')):
            if not p.is_file():continue
            name=p.relative_to(r.ROOT).as_posix()
            if not (name.startswith(prefixes) or name.split('/')[0] in callers
                    or '/' not in name and p.suffix in ('.cs','.csproj','.json')):continue
            data=p.read_bytes();z.writestr(name,data)
            records[name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,record in records.items():assert hashlib.sha256(z.read(name)).hexdigest()==record['sha256']
    evidence={p.relative_to(r.REPO).as_posix():r.sha(p) for p in r.REPORT.rglob('*')
              if p.is_file() and p.name not in ('reproduction.zip','reproduction.manifest.json','cleanup.json')}
    for p in (r.REPO/'benchmarks/disassembly').glob('*'):
        if p.is_file():evidence[p.relative_to(r.REPO).as_posix()]=r.sha(p)
    r.save('reproduction.manifest.json',dict(archive_sha256=r.sha(archive),files=records,repository_evidence=evidence,
        exclusions='CLI homes, compiler caches and intermediate artifacts. No catalog, credentials, signing files or service data were created.'))
    print(f'Verified {len(records)} archive files; SHA256 {r.sha(archive)}',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='audit':audit()
    elif sys.argv[1]=='archive':archive()
    else:raise ValueError(sys.argv[1])
