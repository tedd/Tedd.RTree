"""Audit coverage/provenance after the complete fixed budgets; no timing selection."""
import sys
sys.dont_write_bytecode=True
import json,subprocess
import research as r

def main():
    budgets=dict(exploration=72,columns=72,keys=54,guards=72,**{'leaf-columns':72,'capacities':72,'small-radix':36,'confirmation':60,'tiered':36,'comparison':234,'boundary':18})
    records=[]
    for phase,count in budgets.items():
        folder=r.EVIDENCE/phase
        plan=json.loads((folder/'protocol.json').read_text());launches=json.loads((folder/'launches.json').read_text());samples=json.loads((folder/'samples.json').read_text())
        assert len(plan['jobs'])==len(launches)==len(list(folder.glob('*.out')))==count
        assert r.digest(folder/'driver.py.txt')==plan['driver']
        assert all(x['us']>0 and x['repetitions']>0 and (x['allocated'] is None or x['allocated']>=0) for x in samples)
        for job,launch in zip(plan['jobs'],launches):
            if phase=='boundary':
                b,tier,m=job;assert (launch['block'],launch['mode'])==(b,m+('-tiered' if tier else '-fullopts'))
            else:assert tuple(job)==tuple(launch[k] for k in ('block','size','distribution','mode'))
            assert 'validated=' in launch['validation']
        # Every protocol job supplies one complete build and four query groups.
        assert len([x for x in samples if x['operation']=='build'])==count
        assert all(len([x for x in samples if x['operation']=='query'+str(g)])==count for g in range(4))
        records.append(dict(phase=phase,processes=count,observations=len(samples),complete=True))
    selected=json.loads((r.REPORT/'selection.json').read_text())
    actual_baseline={p.name:r.digest(p) for p in (r.REPO/'src/Tedd.RTree').glob('*.cs')}
    # Preserve the frozen setup-resumption inventory, including its two proposal-only entries.
    extras=sorted(set(selected['baseline'])-set(actual_baseline))
    assert extras==['IReadOnlySpatialIndex.cs','PackedRTree.cs']
    assert {k:selected['baseline'][k] for k in actual_baseline}==actual_baseline
    assert selected['source']=={p.name:r.digest(p) for p in (r.ROOT/'proposal-source/src/Tedd.RTree').glob('*.cs')}
    actual=r.digest(r.ROOT/'proposal-library/Tedd.RTree.dll')
    for phase in ('confirmation','tiered','comparison'):
        assert json.loads((r.EVIDENCE/phase/'protocol.json').read_text())['library']==actual
    for mode in ('mutable','packed'):
        for operation in ('query','build'):
            folder=r.REPORT/('dotnetlab-'+mode)/operation
            capture=json.loads((folder/'capture-operation.json').read_text());analysis=json.loads((folder/'analysis-operation.json').read_text())
            assert capture['state']==analysis['state']=='completed'
            record=json.loads(json.loads((folder/'capture-record.json').read_text())['data']['json'])
            assert r.digest(folder/'capture.nettrace')==record['artifact_id'][4:]
    subprocess.run(['git','apply','--check',str(r.REPORT/'specialization.patch')],cwd=r.REPO,check=True)
    subprocess.run(['git','diff','--quiet','--','src/Tedd.RTree'],cwd=r.REPO,check=True)
    result=dict(epochs=records,total_processes=sum(x['processes'] for x in records),frozen_library=actual,production_sources_unchanged=True,baseline_inventory_extra_proposal_files=extras,patch_check=True,four_verified_captures=True)
    manifest_path=r.REPORT/'reproduction.manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        available={v['sha256'] for v in manifest['files'].values()}|set(manifest['repository_evidence'].values())
        bindings={}
        for phase in budgets:
            protocol=json.loads((r.EVIDENCE/phase/'protocol.json').read_text())
            bindings[phase]={k:protocol[k] in available for k in ('library','caller','caller_source') if k in protocol}
            assert all(bindings[phase].values())
            assert all(v in available for v in protocol.get('library_source',{}).values())
        result['retained_measured_artifact_bindings']=bindings
    (r.REPORT/'coverage-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
