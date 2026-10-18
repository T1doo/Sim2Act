"""Independent closed-file/Git audit; never import product code or open a DB."""
import ast
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('/workspace/production-trial-journal-20261018')
RUN = ROOT / 'run-1'
OUT = Path('/workspace/production-trial-journal-review-20261018')
REPO = Path('/workspace/Sim2Act')
FREEZE = '12958af924fad425fa619adccd1841fb8f8228a8'
BASE = '080ea7b184a7476019431c1803b4bfe4864afbd9'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    assert '.db' not in path.name
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=REPO)


def fp(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode())


manifest_raw = (ROOT / 'sealed-manifest.json').read_bytes()
assert sha(manifest_raw) == 'c5057f6b9c371ff03e5f7bef1e8eeb660fc71a613854cee096cb82d3e8235d91'
manifest = json.loads(manifest_raw)
verified = []
for name, expected in manifest['files'].items():
    path = ROOT / name
    assert not path.is_symlink() and '.db' not in path.name
    raw = path.read_bytes()
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    verified.append({'path': name, **expected})
assert len(verified) == 55 and sum(x['bytes'] for x in verified) == 363044
closure = load(ROOT / 'closure.json')
assert len(closure['physical_fixture_databases']) == 12
for item in closure['physical_fixture_databases']:
    path = ROOT / item['path']
    assert not path.is_symlink() and path.stat().st_size == item['bytes']
before, after = (load(RUN / name) for name in ('inputs-before.json', 'inputs-after.json'))
assert before == after and before['head'] == FREEZE and len(before['inputs']) == 703
assert sum(p.startswith('src/') for p in before['inputs']) == 136
for name, expected in before['inputs'].items():
    raw = git('show', FREEZE + ':' + name)
    assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    assert raw == (REPO / name).read_bytes()
new_paths = ['src/sim2act/production_trial_journal.py', 'tests/test_production_trial_journal.py']
changed = git('diff', '--name-only', BASE, FREEZE).decode().splitlines()
assert changed == new_paths
for name in new_paths:
    assert (RUN / 'frozen-source' / name).read_bytes() == git('show', FREEZE + ':' + name)
helpers = load(RUN / 'helpers-before.json')
assert helpers == load(RUN / 'helpers-after.json')
for key, name in (('runner', 'runner.py'), ('guard', 'offline_policy_guard.py')):
    raw = (RUN / name).read_bytes()
    assert len(raw) == helpers[key]['bytes'] and sha(raw) == helpers[key]['sha256']
suite = ET.parse(RUN / 'junit.xml').getroot()
cases = list(suite.iter('testcase'))
assert len(cases) == len({(c.get('classname'), c.get('name')) for c in cases}) == 12
assert not any(list(suite.iter(t)) for t in ('failure', 'error', 'skipped'))
assert len(re.findall(r'^tests/.+ PASSED$', (RUN / 'pytest.stdout').read_text(), re.M)) == 12
assert (RUN / 'pytest.stderr').read_bytes() == b''
execution = load(RUN / 'execution.json')
assert execution['source_commit'] == FREEZE and execution['exit_code'] == 0
assert not execution['input_drift'] and not execution['helper_drift']
assert load(RUN / 'offline-guard.json')['attempts'] == []


def receipt(value):
    assert value['scope'] == 'UNINSTALLED_DURABLE_JOURNAL_ONLY'
    assert value['live_allowed'] is value['dispatch_authorized'] is value['real_source_verified'] is False
    assert len(value['ledger']['slots']) == 1
    slot, scope = value['ledger']['slots'][0], value['ledger']['scope']
    item = slot['identity']
    assert item['requirements_fingerprint'] == fp(scope)
    assert item['account_id'] == value['ledger']['account_id'] == value['quota']['account_id']
    assert item['quota_subject'] == scope['quota_subject'] == value['quota']['quota_subject']
    assert scope['quota_subject'] == 'intern-ai-account-' + sha(item['account_id'].encode())
    assert item['wire_sha256'] == sha(b'{"synthetic_durable_journal":true}') and item['wire_bytes'] == 34
    assert value['quota']['last_reserved_at'] == slot['reserved_at'] and scope['paid_cap'] == 0
    return slot


races = []
for name in manifest['files']:
    if not name.endswith('/linearization.json'):
        continue
    item = load(ROOT / name)
    trace, first = item['trace'], item['first']
    label = 'marker' if first == 'marker' else 'control'
    assert trace.index(label + '-written-lock-held') < trace.index('contender-BEGIN-attempt')
    assert trace.index('contender-BEGIN-attempt') < trace.index('both-active-before-release')
    assert trace.index('both-active-before-release') < trace.index(label + '-released')
    slot = receipt(item['settled'])
    assert item['independent_connections'] == 2
    assert slot['attempted'] == (first == 'marker') and not slot['accepted']
    assert item['settled']['ledger']['halted'] and slot['settlement']['total_tokens'] == 8
    assert item['settled']['revision'] == item['settled']['quota_revision'] == (3 if first == 'marker' else 2)
    assert item['marker_result'] == ('committed' if first == 'marker' else 'VERSION_CONFLICT')
    races.append({'path': name, 'first': first, 'change': item['change'],
                  'revision': item['settled']['revision'], 'attempted': slot['attempted']})
assert len(races) == 6
assert {(r['first'], r['change']) for r in races} == {
    (a, b) for a in ('marker', 'control') for b in ('cancel', 'lease', 'fence')}
case = RUN / 'actual-tmp/test_new_process_pending_unkno0'
children = []
for label in ('pending', 'unknown'):
    child = load(case / (label + '-child.stdout'))
    assert child['before'] == child['after'] and child['io_attempts'] == []
    assert (case / (label + '-child.stderr')).read_bytes() == b''
    assert child['duplicate']['duplicate'] and not child['duplicate']['changed']
    slot = receipt(child['after'])
    assert child['duplicate']['ledger'] == child['after']['ledger']
    assert child['duplicate']['revision'] == child['after']['revision'] == (1 if label == 'pending' else 3)
    assert slot['attempted'] == (label == 'unknown')
    if label == 'unknown':
        assert child['after']['ledger']['halted'] and not slot['accepted']
        assert slot['settlement']['prompt_tokens'] == 5
        assert slot['settlement']['completion_tokens'] is slot['settlement']['total_tokens'] is None
    else:
        assert slot['settlement'] is None and not child['after']['ledger']['halted']
    children.append({'label': label, 'revision': child['after']['revision'], 'io_attempts': []})
same = load(RUN / 'actual-tmp/test_two_stores_same_attempt_o0/concurrent-same-attempt.json')
assert sorted(r['duplicate'] for r in same['results']) == [False, True]
assert all(r['revision'] == r['quota_revision'] == 1 for r in same['results'])
for r in same['results']:
    receipt(r)
assert receipt(same['final'])['accepted'] and same['final']['revision'] == 3
cross = load(RUN / 'actual-tmp/test_one_account_across_two_pr0/cross-project-account-contention.json')
assert len(cross['results']) == 2 and cross['results'].count('RATE_LIMITED') == 1
assert cross['empty_or_forged_trial_cursor_reads'] == []
assert receipt(cross['winner_state'])['settlement'] is None
assert cross['winner_state']['revision'] == cross['winner_state']['quota_revision'] == 1
cas = load(RUN / 'actual-tmp/test_stale_revision_and_mid_pa0/atomic-cas-rollback.json')
assert cas['all_55_tables_strict_equal'] is True
assert cas['injection'] == ['stale quota fingerprint after both ledger CAS writes']
assert not receipt(cas['state'])['attempted'] and cas['state']['revision'] == cas['state']['quota_revision'] == 1
journal_states = []
for name in manifest['files']:
    if name.endswith('/journal-state.json'):
        state = load(ROOT / name)
        assert state['unchanged_other_tables'] is True and state['except_controlled_tables'] == ['runs', 'events']
        assert state['provider_calls'] == state['live_permits'] == 0
        assert len(state['mirrors']) == state['row_count'] == (3 if 'test_missing_mirror' in name else 4)
        journal_states.append(name)
assert len(journal_states) == 11
importers = []
for path in (REPO / 'src/sim2act').glob('*.py'):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and ((node.module or '').endswith('production_trial_journal')
                or any(n.name == 'production_trial_journal' for n in node.names)):
            importers.append(str(path.relative_to(REPO)))
        if isinstance(node, ast.Import) and any(n.name.endswith('production_trial_journal') for n in node.names):
            importers.append(str(path.relative_to(REPO)))
assert importers == []
design_bridge = load(ROOT / 'design-revision-bridge.json')
assert sha((ROOT / 'minimal-design-reviewed-v1.md').read_bytes()) == design_bridge['reviewed_original_sha256']
assert sha((ROOT / 'minimal-design.md').read_bytes()) == design_bridge['current_sha256']
result = {'status': 'PASS_CLOSED_FILE_GIT_AUDIT', 'freeze': FREEZE, 'baseline': BASE,
    'manifest_sha256': sha(manifest_raw), 'verified_files': verified,
    'non_db_files': 55, 'non_db_bytes': 363044, 'db_stat_only': 12,
    'inputs_each_run': 703, 'production_inputs': 136, 'old_inputs_unchanged': 701,
    'old_production_unchanged': 135, 'helper_drift': False, 'junit_unique': 12,
    'passed': 12, 'failed': 0, 'junit_seconds': float(next(suite.iter('testsuite')).get('time')),
    'outer_seconds': execution['elapsed_seconds'], 'race_orderings': races, 'new_process_reads': children,
    'journal_state_artifacts': journal_states, 'read_unowned_cursor_negative': 'two refusals and calibrated query counter zero',
    'cas_evidence': 'executed all55 strict equality assertion plus returned revision1; no raw-row reconstruction',
    'importers': [], 'guard_attempts': [], 'old_19_nodes_rerun': 0,
    'reviewer_product_pytest_db_sql_http_network_executions': 0}
(OUT / 'qualification-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('status', 'freeze', 'non_db_files', 'non_db_bytes',
    'db_stat_only', 'inputs_each_run', 'production_inputs', 'old_inputs_unchanged', 'junit_unique', 'passed',
    'failed', 'junit_seconds', 'outer_seconds', 'old_19_nodes_rerun')}, indent=2))
