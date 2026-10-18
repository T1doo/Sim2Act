import ast
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-policy-kernel-20261018')
assert not (out / 'sealed-manifest.json').exists()
record = json.loads((out / 'execution.json').read_text())
assert record['source_commit'] == 'c62bfb90d23234c6ce56c78bf6c441d6ca1a7703'
assert record['exit_code'] == 0 and not record['input_drift'] and not record['helper_drift']
assert not subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain=v1','--untracked-files=all'],cwd=repo)
assert json.loads((out / 'inputs-before.json').read_text()) == json.loads((out / 'inputs-after.json').read_text())
assert json.loads((out / 'helpers-before.json').read_text()) == json.loads((out / 'helpers-after.json').read_text())
suite = ET.parse(out / 'junit.xml').getroot()
cases = list(suite.iter('testcase'))
assert len(cases) == 19 and not any(list(suite.iter(tag)) for tag in ('failure','error','skipped'))
guard = json.loads((out / 'offline-guard.json').read_text())
assert guard['attempts'] == [] and guard['pytest_exitstatus'] == 0
directories = sorted(p for p in (out / 'actual-tmp').iterdir() if p.is_dir() and not p.is_symlink())
proofs = sorted(p for directory in directories for p in directory.glob('*.json'))
windows = []
for proof in proofs:
    if proof.name == 'policy-readonly-windows.json':
        item = json.loads(proof.read_text())
        windows.extend(item['windows'])
assert len([p for p in proofs if p.name == 'policy-readonly-windows.json']) == 7
for window in windows:
    assert window['strict_all_rows_equal'] and len(window['tables']) == 55
    assert all(t['before_sha256'] == t['after_sha256'] for t in window['tables'].values())
protected = ['src/sim2act/' + name for name in (
    'natural_trial_budget.py', 'natural_trial_api.py', 'worker.py', 'production_trial_admission.py',
    'production_evidence.py', 'model.py', 'natural_spec_runtime.py', 'pa_trial_dispatch.py',
    'natural_source_archives.py', 'goal_applications.py', 'pb_live_source_contract.py',
    'text_software_anchors.json', 'text_software_qualification.json')]
stable = {}
for name in protected:
    current = (repo / name).read_bytes()
    baseline = subprocess.check_output(['git','-c','core.fsmonitor=false','show',
        '842a5b46d52131581edcbfa235ef067cc44b809b:' + name],cwd=repo)
    assert current == baseline
    stable[name] = dict(bytes=len(current),sha256=hashlib.sha256(current).hexdigest(),baseline_identical=True)
importers = []
for path in (repo / 'src/sim2act').glob('*.py'):
    if path.name == 'production_trial_policy.py':
        continue
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and (
                (node.module or '').endswith('production_trial_policy')
                or any(alias.name == 'production_trial_policy' for alias in node.names)):
            importers.append(str(path.relative_to(repo)))
assert not importers
for name in ('src/sim2act/natural_live_admission.py', 'src/sim2act/production_trial_policy.py',
             'tests/test_production_trial_policy.py'):
    target = out / 'frozen-source' / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(repo / name,target)
shutil.copyfile('/workspace/run-production-policy-kernel-20261018.py',out / 'runner.py')
shutil.copyfile(__file__,out / 'close-evidence.py')
closure = dict(source_commit=record['source_commit'], baseline='842a5b46d52131581edcbfa235ef067cc44b809b',
    unique_nodes=19, executions=19, passed=19, failed=0,
    junit_seconds=float(next(suite.iter('testsuite')).attrib['time']),outer_seconds=record['elapsed_seconds'],
    input_count=record['input_count'],production_count=record['production_count'],input_drift=False,helper_drift=False,
    policy_nodes=7,old_context_nodes=12,policy_operation_windows=len(windows),tables_per_window=55,
    strict_all_rows_equal_executed=True,
    row_evidence='per-table row counts/fingerprints plus executed strict equality assertion; not full-row export or independent DB reconstruction',
    kernel_importers=importers,protected_files=stable,
    source_authority='ABSENT',source_results='SYNTHETIC_INTERNAL_TEST_INPUTS_ONLY',
    new_live_permits=0,provider_calls=0,worker_once_calls=0,
    storage_installation='NOT_INSTALLED',global_db_quota_concurrency='NOT_TESTED_OR_INSTALLED',
    serialized_state='JSON_ROUNDTRIP_ONLY',software_literal_qualification='NOT_RUN_OR_REPINNED',
    not_run=['production source/fee/account verification','real provider/model/semantics','native Windows','PostgreSQL','remote CI',
        'old cancelled exact-install window','UI/full P-A/P-B model chain','durable controller/CAS/global quota installation'])
(out / 'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
files = sorted([p for p in out.iterdir() if p.is_file()] + proofs + list((out / 'frozen-source').rglob('*.py')))
databases = sorted(p for directory in directories for p in directory.glob('fixture.db*') if p.is_file())
manifest = dict(scope='SEALED raw execution files; excludes pytest current aliases and this manifest',files={
    str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files},
    retained_fixture_database_files={str(p.relative_to(out)):dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),copied=False) for p in databases})
target = out / 'sealed-manifest.json'
target.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(files_excluding_manifest=len(files),bytes_excluding_manifest=sum(e['bytes'] for e in manifest['files'].values()),
    database_paths=len(databases),policy_windows=len(windows),junit_seconds=closure['junit_seconds'],
    manifest_sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
