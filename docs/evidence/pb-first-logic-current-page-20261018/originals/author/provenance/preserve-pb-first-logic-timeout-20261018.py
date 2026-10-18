import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

root=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
old=root/'timed-out-2'
assert not old.exists()
execution=json.loads((root/'execution.json').read_text())
assert execution['exit_code']==124 and execution['command'][2]=='900s'
assert (root/'actual.exit').read_text().strip()=='124'
case=next(p.parent for p in root.glob('actual-tmp/**/progress.jsonl'))
progress=[json.loads(line) for line in (case/'progress.jsonl').read_bytes().split(b'\n')[:-1]]
node=next(row['pid'] for row in progress if row['kind']=='node_started')
node_proc=Path('/proc',str(node))
node_state=next((line for line in (node_proc/'status').read_text().splitlines() if line.startswith('State:')), 'ABSENT') if node_proc.exists() else 'ABSENT'
assert node_state=='ABSENT' or 'Z (zombie)' in node_state, node_state
known=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:args=(proc/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    if b'/workspace/pb-first-logic-current-page-evidence-20261018/run-targeted.py' in args or b'tests/test_pb_first_logic_current_page_ui.py' in args or b'/workspace/Sim2Act/tests/pb_first_logic_current_page_ui.cjs' in args:
        known.append(int(proc.name))
assert known==[],known
old.mkdir()
rows=[]
for name in ['actual-tmp','execution.json','actual.stdout','actual.stderr','actual.exit','actual-junit.xml']:
    source=root/name
    if not source.exists():continue
    for path in sorted(source.rglob('*')) if source.is_dir() else [source]:
        if path.is_file() and not path.is_symlink():
            data=path.read_bytes();rows.append(dict(path=str(path.relative_to(root)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    source.rename(old/name)
for row in rows:
    data=(old/row['path']).read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
(old/'retained-original-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
runner=root/'run-targeted.py'
for target in [old/'run-targeted-as-executed.py',root/'interrupted-1/run-targeted-as-executed.py']:
    assert not target.exists();shutil.copyfile(runner,target)
case=next(p.parent for p in old.glob('actual-tmp/**/progress.jsonl'))
counts={name:len(json.loads((case/(name+'-wire.json')).read_text())) for name in ['generation','source-original','pb-original','logic-check','logic-use']}
workers=json.loads((case/'business-workers.json').read_text())
http=json.loads((case/'page-http.json').read_text())
record=dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(),classification='EXTERNAL_WHOLE_CASE_900_SECOND_TIMEOUT_EXIT124_NOT_A_PASS',source_sha=execution['head'],exit_code=124,whole_case_seconds=execution['duration_seconds'],node_pid=node,owned_node_proc_state=node_state,owned_node_executable=False,owned_live_process_matches=known,owned_zombie_not_signalled_or_modified=True,retained_original_files=len(rows),saved_mock_counts=counts,saved_business_workers=workers,observed_page_posts=[dict(path=row['path'],status=row['status']) for row in http if row['method']=='POST'],junit_exists=(old/'actual-junit.xml').exists(),page_result_exists=(case/'page-result.json').exists(),proof_exists=(case/'proof.json').exists(),last_saved_http=[dict(path=row['path'],status=row['status'],elapsed_seconds=row['elapsed_seconds']) for row in progress if row['kind']=='http_response_saved'][-1],cause='GNU timeout returned124 after900.207s; outer guard counted normal fixture preparation plus complete page and cut off terminal refresh/cold-read tail before pytest completion.',harness_correction='Set only whole-case external guard1200s so fixture time does not consume the page owned-Node900s guard. Product Run300s/lease30s and all code/quality checks remain unchanged.',test_qualification='INCOMPLETE_NOT_PASS',retry='one complete same-source attempt with corrected whole-case harness guard; no replay/resume of this partial fixture')
assert sum(counts.values())==11 and len(workers)==4 and all(row['status']=='SUCCEEDED' for row in workers)
(old/'timeout-classification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
s=runner.read_text();assert s.count("'900s'")==1
runner.write_text(s.replace("'900s'","'1200s'"))
print(json.dumps(record,ensure_ascii=False))
