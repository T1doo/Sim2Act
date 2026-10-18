import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path('/workspace/Sim2Act')
root = Path('/workspace/production-policy-kernel-followup-20261018')
assert not (root / 'sealed-manifest.json').exists()
execution = json.loads((root / 'execution.json').read_text())
assert execution['source_commit'] == '20a43aba27e6276046cd9ae25ac090f02bff89ba'
assert execution['exit_code'] == 0 and not execution['input_drift'] and not execution['helper_drift']
assert json.loads((root / 'inputs-before.json').read_text()) == json.loads((root / 'inputs-after.json').read_text())
suite = ET.parse(root / 'junit.xml').getroot()
assert len(list(suite.iter('testcase'))) == 1
assert not any(list(suite.iter(tag)) for tag in ('failure','error','skipped'))
directories = [p for p in (root / 'actual-tmp').iterdir() if p.is_dir() and not p.is_symlink()]
assert len(directories) == 1
proofs = sorted(directories[0].glob('*.json'))
windows = json.loads((directories[0] / 'policy-readonly-windows.json').read_text())['windows']
assert len(windows) == 5
for window in windows:
    assert window['strict_all_rows_equal'] and len(window['tables']) == 55
    assert all(t['before_sha256'] == t['after_sha256'] for t in window['tables'].values())
cancelled = json.loads((directories[0] / 'cancel-after-reservation.json').read_text())
slot = cancelled['ledger']['slots'][0]
assert slot['attempted'] is True and slot['accepted'] is False and cancelled['ledger']['halted'] is True
assert slot['settlement']['total_tokens'] == 8
assert json.loads((root / 'offline-guard.json').read_text())['attempts'] == []
target = root / 'frozen-source/tests/test_production_trial_policy.py'
target.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(repo / 'tests/test_production_trial_policy.py',target)
shutil.copyfile('/workspace/run-production-policy-kernel-followup-20261018.py',root / 'runner.py')
shutil.copyfile(__file__,root / 'close-evidence.py')
closure = dict(source_commit=execution['source_commit'],production_source='c62bfb90d23234c6ce56c78bf6c441d6ca1a7703',
    unique_cancel_node=1,executions=1,passed=1,failed=0,junit_seconds=float(next(suite.iter('testsuite')).attrib['time']),
    outer_seconds=execution['elapsed_seconds'],input_count=701,production_count=135,input_drift=False,helper_drift=False,
    product_source_changed=False,other_18_nodes_reexecuted=False,policy_windows=5,tables_per_window=55,
    attempted_before_cancel=True,known_usage_kept=8,accepted_after_cancel=False,halted=True,
    aggregate_unique_nodes=19,aggregate_executions=20,aggregate_passed=20,aggregate_failed=0,
    note='Stronger cancellation oracle only; first run remains preserved, no production bug fix or source change',
    no_real_source_or_live_permit_or_model_calls=True,not_durable_or_global_quota_installation=True)
(root / 'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
files = sorted([p for p in root.iterdir() if p.is_file()]+proofs+[target])
dbs = sorted(directories[0].glob('fixture.db*'))
manifest = dict(scope='SEALED bounded cancellation followup, excludes pytest current aliases and itself',files={
    str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files},
    retained_fixture_database_files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),copied=False) for p in dbs})
path = root / 'sealed-manifest.json'
path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(files_excluding_manifest=len(files),bytes_excluding_manifest=sum(e['bytes'] for e in manifest['files'].values()),
    junit_seconds=closure['junit_seconds'],database_paths=len(dbs),manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
