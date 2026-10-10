import hashlib
import json
import re
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
raw = raw_path.read_text()
records = []
segments = []
summary = None
tracking = False
for line in raw.splitlines():
    text = re.sub(r'^\d{4}-\d\d-\d\dT[^ ]+ ', '', line)
    if 'SIM2ACT_CI_DIAGNOSTIC ' in text:
        record = json.loads(text.split('SIM2ACT_CI_DIAGNOSTIC ', 1)[1])
        records.append(record)
        if record['event'] == 'node_start':
            tracking = True
            segments.append({'nodeid': record['nodeid'], 'utc': record['utc'], 'progress': []})
        elif record['event'] in ('interrupted', 'session_finish'):
            tracking = False
    elif text.startswith('Engineering diagnostics: '):
        summary = json.loads(text.removeprefix('Engineering diagnostics: '))
    elif tracking and segments and re.fullmatch(r'[.sFE]+(?:\s+\[\s*\d+%\])?', text.strip()):
        segments[-1]['progress'].append(text.strip())
failures = [r for r in records if r['event'] == 'collection_failed' or (r['event'] == 'node_report' and r['outcome'] == 'failed')]
target_path = Path(__file__).parent / 'targets.json'
if not target_path.exists():
    target_path = Path(__file__).parent.parent / 'author/targets.json'
targets = json.loads(target_path.read_text())
by_node = {s['nodeid']: s for s in segments}
target_results = []
for target in targets:
    segment = by_node.get(target)
    failed = [r for r in failures if r.get('nodeid') == target]
    if failed:
        status = 'FAIL'
    elif segment is None:
        status = 'NOT_RUN'
    elif segment['progress'] == ['.']:
        status = 'PASS: actual pytest progress dot'
    elif segment['progress'] == ['s']:
        status = 'SKIP: actual pytest progress'
    else:
        status = 'INCOMPLETE_OR_NOT_RECORDED'
    target_results.append(dict(nodeid=target, status=status, progress=None if segment is None else segment['progress']))
result = dict(full_log_private_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(), summary=summary, failures=failures, visible_records=len(records), target_results=target_results, progress_count=sum(len(''.join(s['progress'])) for s in segments), segments_count=len(segments))
output = raw_path.with_suffix('.parsed.json')
output.write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k,v in result.items() if k not in ('failures','target_results')}, indent=2))
print(json.dumps({'target_statuses': {status: sum(r['status']==status for r in target_results) for status in sorted({r['status'] for r in target_results})}, 'failure_count': len(failures)}))
