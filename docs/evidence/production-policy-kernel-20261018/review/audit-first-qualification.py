"""Independent file/Git audit only; no product imports, DB, network or tests."""
import ast
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path('/workspace/production-policy-kernel-20261018')
REPO = Path('/workspace/Sim2Act')
OUT = Path('/workspace/production-policy-kernel-review-20261018')
FREEZE = 'c62bfb90d23234c6ce56c78bf6c441d6ca1a7703'
BASE = '842a5b46d52131581edcbfa235ef067cc44b809b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    assert path.suffix != '.db' and '.db-' not in path.name
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=REPO)


def fp(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode())


manifest_path = ROOT / 'sealed-manifest.json'
assert sha(manifest_path.read_bytes()) == '92928b53e06c1b4fc12c0b8cdb584f314a1b4cbaa587a73643dfc6460c91fe79'
manifest = load(manifest_path)
verified = []
for name, expected in manifest['files'].items():
    path = ROOT / name
    assert not path.is_symlink() and path.suffix != '.db' and '.db-' not in path.name
    raw = path.read_bytes()
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    verified.append({'path': name, **expected})
assert len(verified) == 36 and sum(v['bytes'] for v in verified) == 983794
db_stats = []
for name, expected in manifest['retained_fixture_database_files'].items():
    path = ROOT / name
    assert not path.is_symlink() and path.stat().st_size == expected['bytes']
    db_stats.append({'path': name, 'bytes': path.stat().st_size, 'stat_only': True})
assert len(db_stats) == 19

before, after = (load(ROOT / name) for name in ('inputs-before.json', 'inputs-after.json'))
assert before == after and before['head'] == FREEZE and len(before['inputs']) == 701
assert sum(p.startswith('src/') for p in before['inputs']) == 135
for name, expected in before['inputs'].items():
    raw = git('show', FREEZE + ':' + name)
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
helpers = load(ROOT / 'helpers-before.json')
assert helpers == load(ROOT / 'helpers-after.json')
for key, name in (('runner', 'runner.py'), ('guard', 'offline_policy_guard.py')):
    raw = (ROOT / name).read_bytes()
    assert len(raw) == helpers[key]['bytes'] and sha(raw) == helpers[key]['sha256']
for name in ('src/sim2act/natural_live_admission.py', 'src/sim2act/production_trial_policy.py',
             'tests/test_production_trial_policy.py'):
    assert (ROOT / 'frozen-source' / name).read_bytes() == git('show', FREEZE + ':' + name)
    if name.startswith('src/'):
        assert (REPO / name).read_bytes() == git('show', FREEZE + ':' + name)

execution = load(ROOT / 'execution.json')
assert execution['source_commit'] == FREEZE and execution['exit_code'] == 0
assert not execution['input_drift'] and not execution['helper_drift']
suite = ET.parse(ROOT / 'junit.xml').getroot()
cases = list(suite.iter('testcase'))
assert len(cases) == len({(x.get('classname'), x.get('name')) for x in cases}) == 19
assert not any(list(suite.iter(t)) for t in ('failure', 'error', 'skipped'))
policy_cases = [x for x in cases if x.get('classname') == 'tests.test_production_trial_policy']
assert len(policy_cases) == 7
stdout = (ROOT / 'pytest.stdout').read_text()
assert len(re.findall(r'^tests/.+ PASSED$', stdout, re.MULTILINE)) == 19
assert (ROOT / 'pytest.stderr').read_bytes() == b''
guard = load(ROOT / 'offline-guard.json')
assert guard['attempts'] == [] and guard['pytest_exitstatus'] == 0

proof_paths = [ROOT / p for p in manifest['files'] if p.endswith('/policy-readonly-windows.json')]
assert len(proof_paths) == 7
windows, table_sets = [], []
for path in proof_paths:
    proof = load(path)
    assert proof['scope'] == 'SYNTHETIC_INPUTS_UNINSTALLED_POLICY_ONLY'
    assert all(proof[k] == 0 for k in ('model_calls', 'worker_once_calls', 'production_permits'))
    for window in proof['windows']:
        assert window['strict_all_rows_equal'] is True and len(window['tables']) == 55
        for table in window['tables'].values():
            assert type(table['rows']) is int and table['rows'] >= 0
            assert table['before_sha256'] == table['after_sha256']
            assert re.fullmatch('[0-9a-f]{64}', table['before_sha256'])
        table_sets.append(set(window['tables']))
        windows.append(window)
assert len(windows) == 46 and all(s == table_sets[0] for s in table_sets)
transitions = {}
for name in manifest['files']:
    if name.endswith(('non-executable-policy-transition.json', 'cancel-after-reservation.json',
                      'unknown-nonrefundable-no-resend.json')):
        state = load(ROOT / name)
        assert state['scope'] == 'UNINSTALLED_POLICY_ONLY'
        assert state['live_allowed'] is state['dispatch_authorized'] is state['real_source_verified'] is False
        slot, scope = state['ledger']['slots'][0], state['ledger']['scope']
        assert len(state['ledger']['slots']) == 1 and scope['paid_cap'] == 0
        identity = slot['identity']
        assert identity['requirements_fingerprint'] == fp(scope)
        assert identity['account_id'] == state['ledger']['account_id'] == state['quota']['account_id']
        assert identity['quota_subject'] == scope['quota_subject'] == state['quota']['quota_subject']
        assert scope['quota_subject'] == 'intern-ai-account-' + sha(identity['account_id'].encode())
        assert identity['wire_sha256'] == sha(b'{"synthetic_policy_only":true}') and identity['wire_bytes'] == 30
        assert state['quota']['last_reserved_at'] == slot['reserved_at']
        transitions[name] = {'attempted': slot['attempted'], 'accepted': slot['accepted'],
                             'halted': state['ledger']['halted'], 'settlement': slot['settlement']}
unknown = next(v for k, v in transitions.items() if k.endswith('unknown-nonrefundable-no-resend.json'))
assert unknown['attempted'] and not unknown['accepted'] and unknown['halted']
assert unknown['settlement']['prompt_tokens'] == 5
assert unknown['settlement']['completion_tokens'] is unknown['settlement']['total_tokens'] is None
cancel = next(v for k, v in transitions.items() if k.endswith('cancel-after-reservation.json'))
assert not cancel['attempted'] and not cancel['accepted'] and cancel['halted']
assert cancel['settlement']['total_tokens'] == 8

closure = load(ROOT / 'closure.json')
protected = {}
assert len(closure['protected_files']) == 13
for name, expected in closure['protected_files'].items():
    raw = (REPO / name).read_bytes()
    assert raw == git('show', BASE + ':' + name) == git('show', FREEZE + ':' + name)
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    protected[name] = expected
importers = []
for path in (REPO / 'src/sim2act').glob('*.py'):
    if path.name == 'production_trial_policy.py':
        continue
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and ((node.module or '').endswith('production_trial_policy')
                or any(n.name == 'production_trial_policy' for n in node.names)):
            importers.append(str(path.relative_to(REPO)))
        if isinstance(node, ast.Import) and any(n.name.endswith('production_trial_policy') for n in node.names):
            importers.append(str(path.relative_to(REPO)))
assert not importers
result = {'status': 'PASS_FILE_GIT_AUDIT_FIRST_19_ONLY', 'freeze': FREEZE,
    'manifest_sha256': sha(manifest_path.read_bytes()), 'verified_non_db_files': verified,
    'db_stat_only': db_stats, 'input_count': 701, 'production_count': 135,
    'input_drift': False, 'helper_drift': False, 'junit_unique': len(cases), 'policy_unique': len(policy_cases),
    'junit_seconds': float(next(suite.iter('testsuite')).get('time')),
    'outer_seconds': execution['elapsed_seconds'], 'windows': len(windows),
    'tables_per_window': 55, 'table_fingerprint_equalities': 46 * 55,
    'window_operation_counts': dict(Counter(w['operation'] for w in windows)),
    'protected_files': protected, 'importers': importers, 'guard_attempts': [],
    'transition_fields': transitions, 'raw_row_reconstruction': False,
    'pending': 'strengthened marked-before-cancel single-node qualification; no first-only final conclusion',
    'audit_executions': 'pure files/Git only; no product, pytest, DB/SQL, HTTP or network'}
(OUT / 'first-qualification-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('status', 'freeze', 'junit_unique', 'windows',
    'tables_per_window', 'table_fingerprint_equalities', 'window_operation_counts', 'pending')}, indent=2))
