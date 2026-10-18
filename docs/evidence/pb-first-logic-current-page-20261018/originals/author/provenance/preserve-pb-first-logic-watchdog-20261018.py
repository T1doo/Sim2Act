import datetime
import hashlib
import json
import shutil
from pathlib import Path

root = Path('/workspace/pb-first-logic-current-page-evidence-20261018')
old = root / 'watchdog-3'
assert not old.exists()
execution = json.loads((root / 'execution.json').read_text())
assert execution['exit_code'] == 1 and execution['command'][2] == '1200s'
assert (root / 'actual.exit').read_text().strip() == '1'
case = next(p.parent for p in root.glob('actual-tmp/**/progress.jsonl'))
progress = [json.loads(line) for line in (case / 'progress.jsonl').read_text().splitlines()]
terminal = progress[-1]
assert terminal['kind'] == 'test_end' and not terminal['passed']
assert terminal['watchdog_fired'] and terminal['node_exit_code'] == -9
node = next(row['pid'] for row in progress if row['kind'] == 'node_started')
assert not Path('/proc', str(node)).exists()
known = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        args = (proc / 'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(item in args for item in [
        b'/workspace/pb-first-logic-current-page-evidence-20261018/run-targeted.py',
        b'tests/test_pb_first_logic_current_page_ui.py',
        b'/workspace/Sim2Act/tests/pb_first_logic_current_page_ui.cjs',
    ]):
        known.append(int(proc.name))
assert known == [], known
old.mkdir()
rows = []
for name in ['actual-tmp', 'execution.json', 'actual.stdout', 'actual.stderr', 'actual.exit', 'actual-junit.xml']:
    source = root / name
    assert source.exists(), name
    for path in sorted(source.rglob('*')) if source.is_dir() else [source]:
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            rows.append(dict(path=str(path.relative_to(root)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    source.rename(old / name)
for row in rows:
    data = (old / row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
(old / 'retained-original-manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
shutil.copyfile(root / 'run-targeted.py', old / 'run-targeted-as-executed.py')
shutil.move(root / 'inputs-after-watchdog-before-correction.json', old / 'inputs-after-watchdog.json')
case = next(p.parent for p in old.glob('actual-tmp/**/progress.jsonl'))
counts = {name: len(json.loads((case / (name + '-wire.json')).read_text())) for name in [
    'generation', 'source-original', 'pb-original', 'logic-check', 'logic-use']}
workers = json.loads((case / 'business-workers.json').read_text())
http = json.loads((case / 'page-http.json').read_text())
assert sum(counts.values()) == 11 and len(workers) == 4
assert all(row['status'] == 'SUCCEEDED' for row in workers)
assert json.loads((case / 'proof.json').read_text())['status'] == 'NOT_COMPLETED'
assert not (case / 'page-result.json').exists()
record = dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    classification='OWNED_NODE_900_SECOND_WATCHDOG_THEN_PYTEST_BROKEN_PIPE_FAILURE_NOT_PASS',
    source_sha=execution['head'], exit_code=1, whole_case_seconds=execution['duration_seconds'],
    node_pid=node, owned_live_process_matches=known, retained_original_files=len(rows),
    saved_mock_counts=counts, saved_business_workers=workers,
    observed_page_posts=[dict(path=row['path'], status=row['status']) for row in http if row['method'] == 'POST'],
    saved_checkpoints=json.loads((case / 'checkpoints.json').read_text()),
    terminal=terminal, cause='Test-only Node watchdog fired at900s from page start during cold second-boot context GET. Owned Node was killed, the normal GET returned200, then Python stdin write raised BrokenPipeError. Pytest exited1 with one failure. Four normal business stages/11Mock complete; no complete cold page or PASS.',
    harness_correction='Parameterize existing test observer with default900 unchanged; only this full P-B case uses owned Node1200s and outer1500s. Preserve all assertions and product run_seconds300/lease30.',
    test_qualification='FAILED_NOT_PASS', retry='one fresh complete attempt after evidence-based test watchdog correction')
(old / 'watchdog-classification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False))
