"""Independent stdlib-only file audit. No product imports, SQL, DB or network."""
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

AUTHOR = Path('/workspace/local-record-collection-export-20261018')
REPO = Path('/workspace/Sim2Act')
CASE = AUTHOR / 'pytest-temp/test_local_record_page_explici0'
REVIEW = Path(__file__).parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

manifest_raw = (AUTHOR / 'sealed-manifest.json').read_bytes()
assert digest(manifest_raw) == 'dac4aa1549e87f4a60e4358719e9700ded04bb34be240a19d19c308d4e7b4aeb'
manifest = json.loads(manifest_raw)['files']
for name, meta in manifest.items():
    path = AUTHOR / name
    assert not path.is_symlink() and '.db' not in name and '.sqlite' not in name
    raw = path.read_bytes()
    assert len(raw) == meta['bytes'] and digest(raw) == meta['sha256'], name
assert len(manifest) == 32 and sum(x['bytes'] for x in manifest.values()) == 5425138

inputs_before, inputs_after = read(AUTHOR / 'input-before.json'), read(AUTHOR / 'input-after.json')
assert inputs_before == inputs_after
for name, meta in inputs_before.items():
    # Hash source/input files only; never physical databases.
    assert '.db' not in name and '.sqlite' not in name
    raw = (REPO / name).read_bytes()
    assert len(raw) == meta['bytes'] and digest(raw) == meta['sha256'], name
freeze = read(AUTHOR / 'final-source-map.json')
copies = {'src/sim2act/web/local-records.js': 'executed-local-records.js',
          'tests/local_record_apps_ui.cjs': 'executed-local_record_apps_ui.cjs',
          'tests/test_local_record_apps_ui.py': 'executed-test_local_record_apps_ui.py'}
assert set(freeze) == set(copies)
for name, copy in copies.items():
    assert (REPO / name).read_bytes() == (AUTHOR / copy).read_bytes()
    assert inputs_before[name] == freeze[name]
source_before, source_after = read(CASE / 'source-before.json'), read(CASE / 'source-after.json')
assert source_before == source_after and read(CASE / 'source-changes.json') == {}

execution = read(AUTHOR / 'execution.json')
assert execution['returncode'] == 0 and execution['source_drift'] == []
tests = ET.parse(AUTHOR / 'result.xml').getroot().findall('.//testcase')
assert len(tests) == 1 and not list(tests[0])
assert tests[0].attrib['name'].endswith('[collection-export]')
assert '1 passed' in (AUTHOR / 'pytest.stdout').read_text()
static = read(AUTHOR / 'static-checks.json')
assert all(row['exit'] == 0 for row in static['checks'])

page = read(CASE / 'page-result.json')
assert page['status'] == 'PASS' and page['scenario'] == 'collection-export'
assert len(page['checks']) == 23 and page['boots'] == 2
assert len(page['actions']) == 34 and all(x['method'] == 'GET' for x in page['actions'])
assets = page['static_resource_loads']
assert len(assets) == 54 and Counter(x['boot'] for x in assets) == {1: 27, 2: 27}
assert read(CASE / 'worker-log.json') == []
summary = read(CASE / 'run-summary.json')
assert summary['node_exit_code'] == 0 and summary['page_worker_calls'] == 0
assert summary['page_post_count'] == 0 and summary['fixture_worker_calls'] == 3
assert summary['real_model_requests'] == 0

info, projection = read(CASE / 'info.json'), read(CASE / 'export-source.json')
fold, prior = {}, None
event_keys = {'namespace','app_id','instance_id','release_id','principal_id','kind',
              'collection_version','record_id','record_revision','previous_event_fingerprint',
              'previous_collection_fingerprint','title','details','state','reason'}
assert projection['id'] == info['instance'] and projection['source_app_id'] == info['app']
assert projection['project_id'] == info['project'] and projection['release_id'] == info['release']
assert projection['namespace'] == 'local-record-app.v1' and projection['formal_publication_enabled'] is False
assert projection['data_version'] == 3 and len(projection['history']) == 3
for version, row in enumerate(projection['history'], 1):
    e = row['event']; assert set(e) == event_keys and row['version'] == version
    assert e['namespace'] == 'local-record-event.v1' and e['collection_version'] == version
    assert e['app_id'] == info['app'] and e['instance_id'] == info['instance']
    assert e['principal_id'] == projection['principal_id'] and e['release_id'] == info['release']
    assert e['previous_collection_fingerprint'] == prior
    assert digest(canonical(e)) == row['event_fingerprint'] == row['artifact']['hash']
    rid = e['record_id']; old = fold.get(rid)
    if e['kind'] == 'CREATE':
        assert old is None and e['record_revision'] == 1 and e['state'] == 'OPEN'
        assert e['previous_event_fingerprint'] is None and e['reason'] == ''
    else:
        assert e['kind'] == 'SET_STATE' and old['state'] == 'OPEN' and e['state'] == 'DONE'
        assert e['record_revision'] == old['record_revision'] + 1
        assert e['previous_event_fingerprint'] == old['last_event_fingerprint']
        assert e['title'] == old['title'] and e['details'] == old['details']
        assert e['reason'] == info['done_reason']
    fold[rid] = {k:e[k] for k in ['record_id','record_revision','title','details','state']}
    fold[rid]['last_event_fingerprint'] = row['event_fingerprint']; prior = row['event_fingerprint']
records = sorted(fold.values(), key=lambda x:x['record_id'])
assert records == sorted(projection['records'], key=lambda x:x['record_id'])
assert len(records) == 2
assert {(r['title'],r['state'],r['record_revision']) for r in records} == {(info['title_a'],'DONE',2),(info['title_b'],'OPEN',1)}

expected = dict(namespace='local-record-collection-snapshot.v1', snapshot_kind='OBSERVED_COMMITTED_COLLECTION',
    principal_id=projection['principal_id'], project_id=info['project'], app_id=info['app'],
    instance_id=info['instance'], release_id=info['release'], release_fingerprint=projection['release_fingerprint'],
    instance_revision=projection['revision'], data_version=3, records=records,
    history=[dict(version=h['version'],run_id=h['run_id'],app_run_id=h['app_run_id'],
        event_fingerprint=h['event_fingerprint'],artifact=dict(resource_id=h['artifact']['resource_id'],hash=h['artifact']['hash']),
        event=h['event']) for h in projection['history']])
expected_raw = (json.dumps(expected, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
assert len(page['downloads']) == 2
for download in page['downloads']:
    raw = base64.b64decode(download['base64'], validate=True)
    assert raw == expected_raw and json.loads(raw.decode('utf-8')) == expected
    assert len(raw) == download['bytes'] == 4957
    assert digest(raw) == download['sha256'] == '79211baa5561b29fe2fb6f872502d4d545a26c1cc9e0a3c11c1f82995fa87263'
    assert download['type'] == 'application/json;charset=utf-8' and download['revoked'] is True
    assert download['filename'] == f"local-records-{info['instance']}-v3.json"
    assert info['pending_title'] not in raw.decode('utf-8')
assert (AUTHOR / 'synthetic-current-collection-v3.json').read_bytes() == expected_raw
assert read(CASE / 'actual-collection-export-proof.json')['snapshot'] == expected

before_fixture = read(CASE / 'database-before-fixture.json')
before, after = read(CASE / 'database-before-page.json'), read(CASE / 'database-after-page.json')
assert set(before_fixture) == set(before) == set(after) and len(before) == 55
changed = [t for t in before if before[t] != after[t]]
assert changed == ['grants']
revocations = read(CASE / 'fixture-revocation-log.json'); assert len(revocations) == 1
rev = revocations[0]; assert rev['run_id'] == info['seed_run'] and rev['resource_id'] == info['seed_artifact']
g0, g1 = {g['id']:g for g in before['grants']}, {g['id']:g for g in after['grants']}
assert g0.keys() == g1.keys() and g0[rev['before']['id']] == rev['before']
assert rev['before']['principal_id'] == projection['principal_id'] and rev['before']['project_id'] == info['project']
assert rev['before']['resource_id'] == info['seed_artifact'] and rev['before']['tool_ref'] == 'resource.read'
assert rev['before']['revoked'] is False
assert rev['after'] == {**rev['before'], 'revoked':True, 'revision':rev['before']['revision']+1}
g0[rev['before']['id']] = rev['after']; assert g0 == g1
workers = read(CASE / 'fixture-worker-log.json'); assert len(workers) == 3
heartbeats = {h['id']:h for h in before['heartbeats']}
assert set(heartbeats) == {w['worker_id'] for w in workers} and not before_fixture['heartbeats']
run_rows = {r['id']:r for r in before['runs']}; assert len(run_rows) == 4
assert run_rows[info['pending_run']]['status'] == 'QUEUED'
assert {w['run_id'] for w in workers} == {h['run_id'] for h in projection['history']}
for w in workers:
    assert w['claimed'] is True and run_rows[w['run_id']]['status'] == 'SUCCEEDED'
    assert w['started_at'] <= heartbeats[w['worker_id']]['at'] <= w['ended_at']
assert before['runs'] == after['runs'] and before['internal_app_runs'] == after['internal_app_runs']
old_grants = {g['id']:g for g in before_fixture['grants']}
new_grants = [g for g in before['grants'] if g['id'] not in old_grants]
assert len(new_grants) == 6
assert all(g in before['grants'] for g in old_grants.values())
for h in projection['history']:
    subset = [g for g in new_grants if g['resource_id'] == h['artifact']['resource_id']]
    assert len(subset) == 2 and {g['principal_id'] for g in subset} == {projection['principal_id'], projection['runtime_id']}
    assert all(g['tool_ref']=='resource.read' and g['project_id']==info['project'] and g['revision']==1 and g['revoked'] is False for g in subset)

http = read(CASE / 'http-trace.json')
wire = Counter((h['method'],h['url'].removeprefix('http://testserver'),h['status'],h['response']) for h in http)
for action in page['actions']:
    key = (action['method'],action['path'],action['status'],action['response_text'])
    assert wire[key] > 0; wire[key] -= 1
held = [a for a in page['actions'] if a.get('controlled_delivery') == 'HELD_AFTER_ACTUAL_HTTP']
assert len(held) == 1 and held[0]['path'] == '/api/internal/record-instances/'+info['instance'] and held[0]['status']==200
denials = [a for a in page['actions'] if a['status'] == 403]
assert len(denials) == 1 and denials[0] is page['actions'][-1] and denials[0]['path']==held[0]['path']
old_run_reads = [json.loads(a['response_text']) for a in page['actions'] if a['path'].endswith('/runs/'+info['seed_run'])]
assert old_run_reads and old_run_reads[0]['result_version'] == 1
ipc = read(CASE / 'ipc.json')
assert [x['value'] for x in ipc if x['direction']=='NODE_TO_PYTHON' and 'id' not in x['value']] == [{'done':True}]
requests = {x['value']['id']:x['value'] for x in ipc if x['direction']=='NODE_TO_PYTHON' and 'id' in x['value']}
responses = {x['value']['id']:x['value'] for x in ipc if x['direction']=='PYTHON_TO_NODE'}
assets_by_path = Counter((x['path'],x['sha256']) for x in assets)
for ident, request in requests.items():
    path = request.get('path','')
    if request.get('method')=='GET' and path and not path.startswith('/api/'):
        response = responses[ident]
        assert response['status']==200
        sha = digest(response['text'].encode('utf-8')); assert assets_by_path[(path,sha)] > 0
        assets_by_path[(path,sha)] -= 1
        disk = REPO / 'src/sim2act/web' / ('index.html' if path=='/' else path.lstrip('/'))
        assert digest(disk.read_bytes()) == sha
assert all(n==0 for n in assets_by_path.values())

out = dict(status='LIMITED_PASS', method='STDLIB_PURE_FILES_ONLY_NO_PRODUCT_IMPORTS_OR_DB',
    author_manifest_sha256=digest(manifest_raw), author_files=len(manifest), author_bytes=sum(x['bytes'] for x in manifest.values()),
    inputs=len(inputs_before), production_inputs=sum(p.startswith('src/') for p in inputs_before), source_drift=0,
    product_freeze=freeze, pytest_unique=1, pytest_executions=1, pytest_pass=1, pytest_fail=0,
    junit_seconds=float(tests[0].attrib['time']), outer_seconds=execution['elapsed_seconds'],
    page_checks=len(page['checks']), page_gets=len(page['actions']), assets=len(assets), boots=2,
    actual_http_trace_entries=len(http), page_http=88, fixture_http=len(http)-88,
    downloads=2, download_bytes=len(expected_raw), download_sha256=digest(expected_raw), independent_event_hash_and_fold=True,
    snapshot_tables=55, page_changed_tables=changed, page_exact_known_grant_revocations=1, page_unchanged_tables=54,
    all_four_runs_unchanged=True, fixture_worker_claims=3, fixture_worker_ids_and_times_verified=True,
    fixture_derived_read_grants=6, queued_fourth_unexecuted=True,
    page_posts=0, page_worker_claims=0, real_models=0,
    limits=['Synthetic ASGI/TestClient and JSDOM/Node Blob; not native browser disk evidence.',
        'No SQLite content opened or hashed. Table audit uses author-retained full JSON exports.',
        'No Windows, PostgreSQL, real user/semantic acceptance, provider/LIVE, remote CI or future push verification.',
        'Held response tests one instance-selection fence; no new broad reliability matrix.'])
(REVIEW / 'final-verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=2))
