"""Normalize local timing and evented Speedscope evidence; no workload execution."""
import collections
import csv
import json
import pathlib
import statistics

RUN = pathlib.Path(__file__).resolve().parent
RAW = RUN / 'raw'
trace = RAW / 'baseline.speedscope.json'
if trace.exists():
    data = json.loads(trace.read_text())
    frames = data['shared']['frames']
    inclusive = collections.Counter()
    exclusive = collections.Counter()
    duration = 0
    for profile in data['profiles']:
        stack = []
        previous = profile.get('startValue', 0)
        for event in profile.get('events', []):
            elapsed = event['at'] - previous
            if stack:
                duration += elapsed
                for frame in set(stack):
                    inclusive[frames[frame]['name']] += elapsed
                leaf = next((frame for frame in reversed(stack) if frames[frame]['name'] not in
                    ('CPU_TIME', 'UNMANAGED_CODE_TIME')), stack[-1])
                exclusive[frames[leaf]['name']] += elapsed
            if event['type'] == 'O': stack.append(event['frame'])
            else:
                assert stack.pop() == event['frame']
            previous = event['at']
    profile = {'unit': 'sampled stack time fraction; includes setup and warmup',
               'total': duration,
               'inclusive': [{'name': k, 'percent': v / duration * 100} for k, v in inclusive.most_common(20)],
               'exclusive': [{'name': k, 'percent': v / duration * 100} for k, v in exclusive.most_common(20)]}
    (RAW / 'profile-summary.json').write_text(json.dumps(profile, indent=2))
    print('Top inclusive frames:', profile['inclusive'][:6])

for path in RAW.glob('*screen.csv'):
    grouped = collections.defaultdict(list)
    for row in csv.DictReader(path.open()):
        grouped[(row['Scenario'], row['Variant'])].append(float(row['Microseconds']))
    summary = []
    for (scenario, variant), values in sorted(grouped.items()):
        summary.append(dict(scenario=scenario, variant=variant, median=statistics.median(values),
                            min=min(values), max=max(values), n=len(values)))
    path.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2))
    print(path.name)
    for row in summary: print(row['scenario'], row['variant'], round(row['median'], 3), round(row['min'], 3), round(row['max'], 3))
