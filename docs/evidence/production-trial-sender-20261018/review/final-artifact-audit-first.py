"""Independent pure file/Git audit; no product import, DB read, pytest or network."""
import ast
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

root = Path('/workspace/production-trial-sender-20261018')
review = Path('/workspace/production-trial-sender-review-20261018')
repo = Path('/workspace/Sim2Act')
freeze = 'c6f946d4d5c90652dbc6ad9945499dc529cc8e4d'
expected_manifest = '86837696b72c0b460154f7d6a467a45b371c88d9671ce87728cdf02edf741c06'
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def readj(path):
    return json.loads(path.read_text())
def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=repo)
def case(name, file):
    return readj(root / 'run-1/actual-tmp' / name / file)
def slot(receipt):
    return receipt['journal']['ledger']['slots'][0]
def disabled(receipt):
    return all(receipt[k] is False for k in ('live_allowed', 'dispatch_authorized', 'real_source_verified', 'business_accepted')) and all(receipt['journal'][k] is False for k in ('live_allowed', 'dispatch_authorized', 'real_source_verified'))

manifest_raw = (root / 'sealed-manifest.json').read_bytes()
assert digest(manifest_raw) == expected_manifest
manifest = json.loads(manifest_raw)
entries = manifest['files']
assert len(entries) == manifest['files_excluding_manifest'] == 61
verified = []
for name, expected in entries.items():
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    assert '.db' not in Path(name).suffixes
    p = root / name
    assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink()
    raw = p.read_bytes()
    assert len(raw) == expected['bytes'] and digest(raw) == expected['sha256'], name
    verified.append({'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
assert sum(x['bytes'] for x in verified) == manifest['bytes_excluding_manifest'] == 388974
closure = readj(root / 'closure.json')
db_stats = []
for item in closure['physical_fixture_databases']:
    p = root / item['path']
    meta = p.stat()  # stat only; no open/read/hash of SQLite bytes
    assert stat.S_ISREG(meta.st_mode) and meta.st_size == item['bytes']
    db_stats.append({'path': item['path'], 'bytes_stat_only': meta.st_size, 'database_read_or_rehash': False})
assert len(db_stats) == 8 and len({x['path'] for x in db_stats}) == 8

execution = readj(root / 'run-1/execution.json')
assert execution['source_commit'] == freeze and execution['exit_code'] == 0
assert execution['command'][-1] == 'tests/test_production_trial_sender.py'
assert execution['command'][:3] == ['timeout', '--kill-after=15s', '240s']
assert execution['old_19_and_12_nodes_rerun'] == 0
xml = ET.fromstring((root / 'run-1/junit.xml').read_bytes())
suite = xml.find('testsuite')
nodes = suite.findall('testcase')
assert suite.attrib['tests'] == '8' and suite.attrib['failures'] == suite.attrib['errors'] == suite.attrib['skipped'] == '0'
assert len(nodes) == len({n.attrib['name'] for n in nodes}) == 8
assert all(len(n) == 0 and n.attrib['classname'] == 'tests.test_production_trial_sender' for n in nodes)
stdout = (root / 'run-1/pytest.stdout').read_text()
assert stdout.count(' PASSED') == 8 and '8 passed, 1 warning' in stdout
assert (root / 'run-1/pytest.stderr').read_bytes() == b''
before = readj(root / 'run-1/inputs-before.json')
after = readj(root / 'run-1/inputs-after.json')
assert before == after and before['head'] == freeze
assert len(before['inputs']) == 705
assert sum(name.startswith('src/') for name in before['inputs']) == 137
for name, item in before['inputs'].items():
    assert '.db' not in Path(name).suffixes
    raw = (repo / name).read_bytes()
    assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], name
hb = readj(root / 'run-1/helpers-before.json')
ha = readj(root / 'run-1/helpers-after.json')
assert hb == ha
for name, path in {'runner': 'runner.py', 'guard': 'offline_sender_guard.py'}.items():
    raw = (root / 'run-1' / path).read_bytes()
    assert len(raw) == hb[name]['bytes'] and digest(raw) == hb[name]['sha256']
assert git('rev-parse', 'HEAD').decode().strip() == freeze
for name in ('src/sim2act/production_trial_sender.py', 'src/sim2act/production_trial_journal.py', 'tests/test_production_trial_sender.py'):
    assert (root / 'run-1/frozen-source' / name).read_bytes() == git('show', freeze + ':' + name) == (repo / name).read_bytes()
static = readj(review / 'freeze-static-review.json')
assert static['freeze'] == freeze and all(static['checks'].values())

normal_dir = 'test_exact_adapter_capture_ato0'
pre_dir = 'test_cancel_between_committed_0'
post_dir = 'test_cancel_after_guard_may_se0'
prefix_dir = 'test_adapter_received_prefix_d0'
cas_dir = 'test_capture_then_journal_cas_0'
normal = case(normal_dir, 'known-body-accounting.json')
pre = case(pre_dir, 'marker-before-guard-cancel.json')
post_proof = case(post_dir, 'guard-to-transport-window.json')
post = post_proof['result']
prefix = case(prefix_dir, 'received-prefix-unknown.json')
cas = case(cas_dir, 'capture-cas-rollback.json')
assert all(disabled(r) for r in (normal, pre, post, prefix, cas['pending']))
raw_object = {'model': 'Intern-S2', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Synthetic 花, no business acceptance'}}], 'usage': {'prompt_tokens': 5, 'completion_tokens': 3, 'total_tokens': 8}}
raw_body = json.dumps(raw_object, ensure_ascii=False, indent=1).encode()
canonical = json.dumps(raw_object, ensure_ascii=True, separators=(',', ':')).encode('ascii')
assert len(raw_body) == 264 and len(canonical) == 209 and digest(raw_body) != digest(canonical)
assert normal['capture_sha256'] == digest(raw_body) and normal['capture_bytes'] == len(raw_body)
assert normal['response_verdict'] == 'VALID_PROTOCOL' and slot(normal)['accepted']
assert slot(normal)['settlement'] == {'outcome': 'RECEIVED', 'response_sha256': digest(raw_body), 'response_ascii_bytes': len(canonical), 'prompt_tokens': 5, 'completion_tokens': 3, 'total_tokens': 8}
assert normal['journal']['revision'] == normal['journal']['quota_revision'] == 3
assert pre['capture_bytes'] == 0 and pre['capture_sha256'] == digest(b'')
assert slot(pre)['attempted'] and not slot(pre)['accepted'] and pre['journal']['ledger']['halted']
assert slot(pre)['settlement']['outcome'] == 'UNKNOWN'
assert all(slot(pre)['settlement'][k] is None for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
assert post_proof['trace'] == ['guard-transaction-finished', 'mock-handler-entered-may-have-sent', 'actual-cancel-committed']
assert post_proof['mock_handler_calls'] == 1 and post['capture_sha256'] == digest(raw_body)
assert slot(post)['settlement']['total_tokens'] == 8 and not slot(post)['accepted'] and post['journal']['ledger']['halted']
prefix_body = json.dumps({'model': 'intern-s2', 'usage': {'prompt_tokens': 5}}).encode()
assert prefix['capture_sha256'] == digest(prefix_body) and prefix['capture_bytes'] == len(prefix_body) == 53
assert slot(prefix)['settlement']['prompt_tokens'] == 5
assert slot(prefix)['settlement']['completion_tokens'] is None and slot(prefix)['settlement']['total_tokens'] is None
assert slot(prefix)['settlement']['outcome'] == 'UNKNOWN' and not slot(prefix)['accepted'] and prefix['journal']['ledger']['halted']
assert cas['all_55_tables_strict_equal_to_marked_checkpoint'] is True and cas['mock_handler_calls'] == 1
pending = cas['pending']
assert pending['journal']['revision'] == 2 and slot(pending)['attempted'] and slot(pending)['settlement'] is None
assert pending['capture_sha256'] is None and not pending['adapter_entered']

state_dirs = [normal_dir, 'test_fixture_and_actual_wire_g0', pre_dir, post_dir, prefix_dir, cas_dir]
states = {d: case(d, 'sender-state.json') for d in state_dirs}
assert all(s['protected_tables_strict_equal'] is True and s['except_controlled_tables'] == ['runs', 'events'] and s['current_worker_live_enabled'] is False and s['real_provider_calls'] == 0 for s in states.values())
assert [states[d]['mock_handler_calls'] for d in state_dirs] == [1, 0, 0, 1, 1, 1]
assert [len(states[d]['mirrors']) for d in state_dirs] == [6, 0, 6, 6, 6, 4]
parent_guard = readj(root / 'run-1/offline-guard.json')
assert parent_guard['attempts'] == [] and parent_guard['pytest_exitstatus'] == 0
assert parent_guard['adapter_methods'].count('request_serialized_captured') == 5
assert parent_guard['adapter_methods'].count('_request_serialized') == 5
assert parent_guard['adapter_methods'].count('_deadline_request') == 4
process_records = []
child_adapters = child_handlers = 0
for idx, phase, expected_exit, expected_handlers in ((0, 'marker-before-adapter', 17, 0), (1, 'received-before-archive', 23, 1)):
    directory = f'test_crashed_sender_new_proces{idx}'
    proof = case(directory, 'process-window-proof.json')
    crash = case(directory, 'crashed-sender-execution.json')
    recovery = case(directory, 'fresh-recovery-execution.json')
    c_lines = [json.loads(line) for line in (root / 'run-1/actual-tmp' / directory / 'crashed-sender.stdout').read_text().splitlines()]
    r_lines = [json.loads(line) for line in (root / 'run-1/actual-tmp' / directory / 'fresh-recovery.stdout').read_text().splitlines()]
    expected_command = ['/workspace/sim2act-venv/bin/python', '-c', 'from test_production_trial_sender import child_main; child_main()']
    assert crash['command'] == recovery['command'] == expected_command
    assert crash['exit_code'] == expected_exit and crash['planned_exit'] is True
    assert recovery['exit_code'] == 0 and recovery['planned_exit'] is False
    assert proof['phase'] == phase and proof['planned_crash_exit'] == expected_exit
    assert proof['actual_mock_handler_calls'] == expected_handlers and proof['fresh_recovery_adapter_calls'] == 0
    assert proof['after_recovery_all_55_tables_strict_equal'] is True
    assert c_lines[0]['event'] == 'actual-child-claim'
    tail = c_lines[-1]
    assert len(tail['sent']) == expected_handlers and tail['io'] == []
    assert tail['methods'].count('request_serialized_captured') == expected_handlers
    if expected_handlers:
        assert tail['received_sha256'] == digest(raw_body)
        assert c_lines[1] == {'event': 'mock-handler', 'count': 1}
    r = r_lines[-1]
    assert r['event'] == 'recovered-history' and r['methods'] == r['sent'] == r['io'] == []
    rr = r['result']
    assert disabled(rr) and rr['journal']['duplicate'] and not rr['journal']['changed']
    assert rr['journal']['revision'] == rr['journal']['quota_revision'] == 2
    assert rr['may_have_sent'] and not rr['adapter_entered'] and rr['capture_sha256'] is None
    assert slot(rr)['identity'] == c_lines[0]['identity'] and slot(rr)['attempted'] and slot(rr)['settlement'] is None and not slot(rr)['accepted']
    child_adapters += tail['methods'].count('request_serialized_captured')
    child_handlers += len(tail['sent'])
    process_records.append({'phase': phase, 'crash_command': expected_command, 'planned_exit': expected_exit, 'recovery_exit': 0, 'mock_handler_calls': expected_handlers, 'fresh_adapter_calls': 0, 'pending_revision': 2})
assert child_adapters == child_handlers == 1
assert parent_guard['adapter_methods'].count('request_serialized_captured') + child_adapters == 6
assert sum(s['mock_handler_calls'] for s in states.values()) + child_handlers == 5
source = (repo / 'tests/test_production_trial_sender.py').read_text()
functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
child_guard = ast.get_source_segment(source, functions['child_guard'])
parent_guard_source = (root / 'run-1/offline_sender_guard.py').read_text()
assert 'socket.socket' not in child_guard
assert 'HTTPTransport.handle_request' in child_guard and 'AsyncHTTPTransport.handle_async_request' in child_guard and 'Settings.from_env' in child_guard
assert "socket.socket,'connect'" in parent_guard_source and "socket.socket,'connect_ex'" in parent_guard_source
normal_ast = ast.get_source_segment(source, functions['test_exact_adapter_capture_atomic_accounting_and_immutable_history'])
empty_ast = ast.get_source_segment(source, functions['test_cancel_between_committed_marker_and_guard_never_reaches_transport'])
assert 'foreign_sql == []' in normal_ast and 'worker' in normal_ast and 'foreign' in normal_ast
assert normal_ast.index('known-body-accounting.json') < normal_ast.index('alter_pair(')
assert empty_ast.index('marker-before-guard-cancel.json') < empty_ast.index('alter_pair(')

result = {
 'status': 'PASS_LIMITED_INDEPENDENT_FILE_GIT_REVIEW_NO_REMAINING_DEFINITE_P1_P2',
 'freeze': freeze, 'author_manifest_sha256': expected_manifest,
 'manifest_files_verified': len(verified), 'manifest_bytes_verified': sum(x['bytes'] for x in verified),
 'author_manifest_bytes': len(manifest_raw), 'verified_non_db_files': verified,
 'database_stat_only': db_stats, 'database_content_reads': 0,
 'qualification': {'unique_nodes': 8, 'executions': 8, 'passed': 8, 'failed': 0, 'junit_seconds': float(suite.attrib['time']), 'outer_seconds': execution['elapsed_seconds'], 'old_19_and_12_nodes_rerun': 0},
 'frozen_inputs': {'all_inputs': 705, 'production': 137, 'before_after_equal': True, 'current_sha_match_all': True, 'helpers_equal': True, 'frozen_git_match': True},
 'processes': process_records,
 'counters': {'parent_synthetic_adapter_calls': 5, 'child_synthetic_adapter_calls': child_adapters, 'total_synthetic_adapter_calls': 6, 'total_mock_handler_calls': 5, 'real_provider_guard_attempts': 0, 'parent_socket_guard': True, 'child_socket_guard': False},
 'known_response_geometry_independently_recomputed': {'raw_bytes': len(raw_body), 'raw_sha256': digest(raw_body), 'canonical_ascii_bytes': len(canonical), 'canonical_ascii_sha256': digest(canonical)},
 'scope_limits': ['Reviewer executed pure file/Git/AST parsing only; no product/pytest/SQL/DB/network', 'Full-row equality is an executed test oracle plus receipts/fingerprints, not independent rehash of DB rows', 'Normal and EMPTY tests deliberately damage new pairs after saving valid receipts; final DBs are not claimed universally valid', 'Child guard covers actual HTTP/env/five Intern paths; it has no socket sentinel', 'No API/Worker installation, source authority, valid LIVE permit, real provider/account/fee/semantic acceptance', 'No full generation/source/cold/UI, PG, Windows/native, remote CI or old 19/12 matrices'],
}
(review / 'final-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'verified_non_db_files'}, ensure_ascii=False, indent=2))
