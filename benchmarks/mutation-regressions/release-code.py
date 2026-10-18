"""Final query equivalence and emitted constructor-call evidence."""
import json
from pathlib import Path
import re

folder=Path(__file__).resolve().parents[2]/'Research/2026-10-18-mutation-regressions'
def sections(path):
    result={}
    for part in path.read_text(encoding='utf8').split('; Assembly listing for method ')[1:]:
        name=part.splitlines()[0]
        instructions=[]
        for line in part.splitlines()[1:]:
            if not re.match(r'^       [a-z]',line):continue
            line=line.split(';',1)[0].strip()
            line=re.sub(r'0x[0-9A-Fa-f]{10,14}(?![0-9A-Fa-f])','<runtime-address>',line)
            instructions.append(re.sub(r'\s+',' ',line))
        result[name]=instructions
    return result
records=[]
for coordinate in ('int','double','long','original'):
    before=sections(folder/f'candidate-{coordinate}-jit.txt')
    after=sections(folder/f'release-{coordinate}-jit.txt')
    for name,old in before.items():
        if not any(':'+method+'(' in name for method in ('Search','CollectValues','BulkLoadPacked')):continue
        assert name in after,'Missing final code'
        new=after[name]
        pattern=r'call .*Tedd\.RTree\.(?:Box|Rectangle).*:\.ctor\(byref,byref\)'
        record=dict(coordinate=coordinate,method=name,equal_normalized_instructions=old==new,
            old_instruction_count=len(old),new_instruction_count=len(new),
            old_union_constructor_calls=sum(bool(re.search(pattern,line)) for line in old),
            new_union_constructor_calls=sum(bool(re.search(pattern,line)) for line in new))
        records.append(record)
        if ':Search(' in name or ':CollectValues(' in name: assert old==new,(name,'Query code changed')
(folder/'release-code-evidence.json').write_text(json.dumps(records,indent=2))
for r in records:print(r['coordinate'],r['method'],r['old_instruction_count'],r['new_instruction_count'],r['old_union_constructor_calls'],r['new_union_constructor_calls'])
