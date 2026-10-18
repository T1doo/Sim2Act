import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-evidence-boundary-20261018')
assert not (out / 'manifest.json').exists()
execution = json.loads((out / 'execution.json').read_text())
assert execution['exit_code'] == 0 and execution['input_drift'] is False
assert execution['head'] == subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
assert not subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=repo)
before, after = (json.loads((out / p).read_text()) for p in ('inputs-before.json', 'inputs-after.json'))
assert before == after
proofpath = next((out / 'actual-tmp').glob('*/actual-production-boundary-proof.json'))
proof = json.loads(proofpath.read_text())
assert len(proof['actual_http']) == 21 and len(proof['source_calls']) == 4
assert len(proof['table_windows']) == 2
for phase in proof['table_windows']:
    assert phase['strict_all_rows_equal'] and len(phase['tables']) == 55
    assert all(t['before_sha256'] == t['after_sha256'] for t in phase['tables'].values())
junit = ET.parse(out / 'junit.xml').getroot()
cases = list(junit.iter('testcase'))
assert len(cases) == 9 and not list(junit.iter('failure')) and not list(junit.iter('error'))
unchanged = [
    'src/sim2act/natural_live_admission.py', 'src/sim2act/natural_trial_budget.py',
    'src/sim2act/natural_trial_api.py', 'src/sim2act/pa_trial_dispatch.py',
    'src/sim2act/pb_natural_uses.py', 'src/sim2act/natural_spec_runtime.py',
    'src/sim2act/model.py', 'src/sim2act/goal_applications.py',
    'src/sim2act/pb_live_source_contract.py', 'src/sim2act/text_software_anchors.json',
    'src/sim2act/text_software_qualification.json']
stable = {}
baseline = '494cf2e1490967f8cf8621bb48b52fa00713436d'
for name in unchanged:
    original = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'show', baseline + ':' + name], cwd=repo)
    actual = (repo / name).read_bytes()
    assert original == actual
    stable[name] = dict(bytes=len(actual), sha256=hashlib.sha256(actual).hexdigest(), baseline_identical=True)
shutil.copyfile('/workspace/run-production-evidence-boundary-20261018.py', out / 'runner.py')
shutil.copyfile(__file__, out / 'close-evidence.py')
metadata = dict(source_commit=execution['head'], baseline=baseline, unique_nodes=9, executions=9,
    passed=9, failed=0, junit_seconds=float(next(junit.iter('testsuite')).attrib['time']),
    outer_seconds=execution['elapsed_seconds'], actual_http_count=21,
    actual_http_status_counts={str(s): sum(v['status'] == s for v in proof['actual_http']) for s in (400, 403, 422)},
    full_table_windows=2, table_count=55, all_rows_strict_equal=True,
    evidence_note='Only per-table fingerprints/row counts and executed strict equality assertion retained; no full-row export or independent DB reconstruction.',
    input_count=execution['input_count'], production_count=execution['production_count'], input_drift=False,
    protected_files=stable, versions={name: importlib.metadata.version(name) for name in ('pytest', 'pydantic', 'fastapi', 'sqlalchemy', 'httpx', 'ruff')},
    source_absent=True, live_permits=0, provider_calls=0, worker_once_calls=0,
    literal_software_qualification='NOT_REACHED', real_fee_authority='ABSENT',
    missing_usage_or_unknown_send_note='No production dispatch is possible. Existing usage/unknown outcome ledger logic unchanged; no new successful send, settlement, resend or live-adapter acceptance claimed.',
    not_run=['real provider/fee/semantic execution', 'native Windows', 'PostgreSQL', 'remote CI', 'old revoked exact-install window'])
(out / 'closure.json').write_text(json.dumps(metadata, indent=2) + '\n')
selected = sorted([p for p in out.iterdir() if p.is_file()] + list((out / 'actual-tmp').glob('*/*.json')))
databases = sorted((out / 'actual-tmp').glob('*/*.db*'))
manifest = dict(scope='closed raw execution evidence; later delivery metadata lives elsewhere', files={
    str(p.relative_to(out)): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in selected},
    retained_fixture_databases={str(p.relative_to(out)): dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(), copied_to_repo=False) for p in databases})
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(source_commit=metadata['source_commit'], raw_files=len(selected), databases=len(databases),
    raw_bytes=sum(x['bytes'] for x in manifest['files'].values()),
    manifest_sha256=hashlib.sha256((out / 'manifest.json').read_bytes()).hexdigest(),
    junit_seconds=metadata['junit_seconds'], statuses=metadata['actual_http_status_counts'])))
