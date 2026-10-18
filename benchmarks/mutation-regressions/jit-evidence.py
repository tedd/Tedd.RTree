"""Compare actual normal-exit query listings; retain normalized instruction evidence."""
import difflib
import json
from pathlib import Path
import re

folder=Path(__file__).resolve().parents[2]/'Research/2026-10-18-mutation-regressions'
def methods(path):
    result={}
    for section in path.read_text(encoding='utf8').split('; Assembly listing for method ')[1:]:
        name=section.splitlines()[0]
        if not any(':'+method+'(' in name for method in ('Search','CollectValues','BulkLoadPacked','BulkLoadCore')): continue
        instructions=[]
        for line in section.splitlines()[1:]:
            if not re.match(r'^       [a-z]',line): continue
            instruction=line.split(';',1)[0].strip()
            instruction=re.sub(r'0x[0-9A-Fa-f]{10,14}(?![0-9A-Fa-f])', '<runtime-address>',instruction)
            instruction=re.sub(r'\s+',' ',instruction)
            instructions.append(instruction)
        result[name]=instructions
    return result
reports=[]
for coordinate in ('int','double','long','original'):
    before=methods(folder/f'baseline-{coordinate}-jit.txt')
    after=methods(folder/f'candidate-{coordinate}-jit.txt')
    assert before and before.keys()==after.keys(), 'Missing or mismatched normal-exit query code'
    for name in before:
        reports.append(dict(coordinate=coordinate,method=name,equal_normalized_instructions=before[name]==after[name],
            baseline_instruction_count=len(before[name]),candidate_instruction_count=len(after[name]),
            differences=list(difflib.unified_diff(before[name],after[name],fromfile='baseline',tofile='candidate'))))
(folder/'query-code-comparison.json').write_text(json.dumps(reports,indent=2))
for report in reports:
    print(report['coordinate'],report['equal_normalized_instructions'],report['method'])
