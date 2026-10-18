"""Read closed JSON/XML/Git only; no product imports or database reads."""
import ast
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('/workspace/production-policy-kernel-followup-20261018')
FIRST = Path('/workspace/production-policy-kernel-20261018')
REPO = Path('/workspace/Sim2Act')
OUT = Path('/workspace/production-policy-kernel-review-20261018')
OLD = 'c62bfb90d23234c6ce56c78bf6c441d6ca1a7703'
NEW = '20a43aba27e6276046cd9ae25ac090f02bff89ba'
TEST = 'tests/test_production_trial_policy.py'
NODE = 'test_cancel_after_reservation_cannot_record_attempt_and_keeps_usage'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    assert '.db' not in path.name
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=REPO)


assert sha((ROOT / 'sealed-manifest.json').read_bytes()) == 'f73291ab1749d7e98d90ec08f93bdf4745010e35a48636ad84330ef2ead803c8'
manifest = load(ROOT / 'sealed-manifest.json')
for name, expected in manifest['files'].items():
    path = ROOT / name
    assert not path.is_symlink() and '.db' not in path.name
    raw = path.read_bytes()
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
assert len(manifest['files']) == 19 and sum(x['bytes'] for x in manifest['files'].values()) == 316310
assert len(manifest['retained_fixture_database_files']) == 1
for name, expected in manifest['retained_fixture_database_files'].items():
    path = ROOT / name
    assert not path.is_symlink() and path.stat().st_size == expected['bytes']
before, after = (load(ROOT / name) for name in ('inputs-before.json', 'inputs-after.json'))
assert before == after and before['head'] == NEW and len(before['inputs']) == 701
old_inputs = load(FIRST / 'inputs-before.json')['inputs']
changed = sorted(p for p in before['inputs'] if before['inputs'][p] != old_inputs[p])
assert changed == [TEST]
assert sum(p.startswith('src/') for p in before['inputs']) == 135
for name, expected in before['inputs'].items():
    raw = git('show', NEW + ':' + name)
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    if name.startswith('src/'):
        assert raw == git('show', OLD + ':' + name) == (REPO / name).read_bytes()
assert (ROOT / 'frozen-source' / TEST).read_bytes() == git('show', NEW + ':' + TEST)
trees = [ast.parse(git('show', ref + ':' + TEST).decode()) for ref in (OLD, NEW)]
old_nodes = {getattr(n, 'name', 'position_' + str(i)): ast.dump(n, include_attributes=False)
             for i, n in enumerate(trees[0].body)}
new_nodes = {getattr(n, 'name', 'position_' + str(i)): ast.dump(n, include_attributes=False)
             for i, n in enumerate(trees[1].body)}
assert old_nodes.keys() == new_nodes.keys()
assert [n for n in old_nodes if old_nodes[n] != new_nodes[n]] == [NODE]
assert load(ROOT / 'helpers-before.json') == load(ROOT / 'helpers-after.json')
for key, name in (('runner', 'runner.py'), ('guard', 'offline_policy_guard.py')):
    raw = (ROOT / name).read_bytes()
    expected = load(ROOT / 'helpers-before.json')[key]
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
suite = ET.parse(ROOT / 'junit.xml').getroot()
cases = list(suite.iter('testcase'))
assert len(cases) == 1 and cases[0].get('name') == NODE
assert not any(list(suite.iter(t)) for t in ('failure', 'error', 'skipped'))
record = load(ROOT / 'execution.json')
assert record['source_commit'] == NEW and record['exit_code'] == 0
assert not record['input_drift'] and not record['helper_drift']
assert (ROOT / 'pytest.stderr').read_bytes() == b''
assert (ROOT / 'pytest.stdout').read_text().count(' PASSED') == 1
assert load(ROOT / 'offline-guard.json')['attempts'] == []
case = ROOT / 'actual-tmp/test_cancel_after_reservation_0'
proof = load(case / 'policy-readonly-windows.json')
assert len(proof['windows']) == 5
for window in proof['windows']:
    assert window['strict_all_rows_equal'] is True and len(window['tables']) == 55
    assert all(t['before_sha256'] == t['after_sha256'] for t in window['tables'].values())
state = load(case / 'cancel-after-reservation.json')
slot = state['ledger']['slots'][0]
assert len(state['ledger']['slots']) == 1 and slot['attempted'] is True
assert slot['accepted'] is False and state['ledger']['halted'] is True
assert slot['settlement']['total_tokens'] == 8
assert state['quota']['last_reserved_at'] == slot['reserved_at']
assert state['live_allowed'] is state['dispatch_authorized'] is state['real_source_verified'] is False
result = {'status': 'PASS_FILE_GIT_FOLLOWUP_AUDIT', 'old_freeze': OLD, 'test_freeze': NEW,
    'non_db_files': 19, 'non_db_bytes': 316310, 'database': 'one stat-only, not opened or rehashed',
    'inputs': 701, 'production': 135, 'run_drift': False, 'changed_inputs': changed,
    'changed_ast_nodes': [NODE], 'production_bytes_equal': True, 'junit_passed': 1,
    'junit_seconds': float(next(suite.iter('testsuite')).get('time')),
    'outer_seconds': record['elapsed_seconds'], 'operation_windows': 5, 'tables_per_window': 55,
    'cancel_attempted': True, 'cancel_accepted': False, 'cancel_halted': True, 'cancel_total_tokens': 8,
    'guard_attempts': [], 'aggregate_unique': 19, 'aggregate_executions': 20,
    'aggregate_passed': 20, 'aggregate_failed': 0,
    'qualification': '18 unchanged nodes on old freeze plus strengthened cancellation on test-only freeze',
    'no_product_pytest_db_sql_http_network_executions_by_reviewer': True}
(OUT / 'followup-qualification-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
