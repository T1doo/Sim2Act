"""Pure file audit. No product imports, subprocess, SQL, DB or network access."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

out = Path('/workspace/correction-chain-reuse-review-20261018')
repo = Path('/workspace/Sim2Act')
first = Path('/workspace/correction-run-http-worker-20261018')
cont = Path('/workspace/correction-run-http-continuation-20261018')

def read(root, name):
    return json.loads((root / name).read_text())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def fp(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode())

expected = {
    first: ('b3da3ecf53cd41f4e37b14a40d6d194202b85398607a8b9697f64d01b952d28c', 17, 814681),
    cont: ('b856f7f99a4ed2e9856b50fba4e31eba4f05f774b31ef2b01859ada59915ca34', 14, 2625031),
}
sealed = []
for root, (wanted, count, size) in expected.items():
    raw = (root / 'sealed-manifest.json').read_bytes()
    assert digest(raw) == wanted
    entries = json.loads(raw)['files']
    assert len(entries) == count and sum(x['bytes'] for x in entries) == size
    checked = []
    for entry in entries:
        relative = Path(entry['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert not any(x in entry['path'].lower() for x in ('.db', '.sqlite', 'holdout'))
        path = root / relative
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], entry['path']
        checked.append(dict(path=entry['path'], bytes=len(data), sha256=digest(data)))
    sealed.append(dict(root=str(root), manifest_sha256=wanted, files=count,
        raw_bytes=size, verified=checked))

first_map = read(first, 'input-before.json')
cont_map = read(cont, 'input-before.json')
assert first_map == read(first, 'input-after.json')
assert cont_map == read(cont, 'input-after.json')
source_keys = [k for k in cont_map if k.startswith('src/')]
assert all(first_map[k] == cont_map[k] for k in source_keys)
assert all(dict(bytes=len((repo/k).read_bytes()), sha256=digest((repo/k).read_bytes())) == cont_map[k]
    for k in source_keys)
bridges = []
for root, mapping in [(first, first_map), (cont, cont_map)]:
    raw = (root / 'executed-harness.cjs').read_bytes()
    expected_entry = mapping['tests/natural_spec_corrections_ui.cjs']
    assert digest(raw) == expected_entry['sha256'] and len(raw) == expected_entry['bytes']
    bridges.append(dict(root=str(root), executed_harness_bytes=len(raw),
        executed_harness_sha256=digest(raw), matches_execution_input=True,
        provenance='reconstructed bytes matching execution input; not an original runtime source copy'
            if root == first else 'retained executed harness'))
current_harness = (repo/'tests/natural_spec_corrections_ui.cjs').read_bytes()
bridges.append(dict(current_harness_sha256=digest(current_harness),
    same_as_continuation=current_harness == (cont/'executed-harness.cjs').read_bytes(),
    qualification='Later readiness/metadata edits are not an additionally executed fresh chain'))

suite = ET.fromstring((first/'result.xml').read_bytes())
cases = list(suite.iter('testcase'))
assert len(cases) == 1 and cases[0].find('failure') is not None
first_exec = read(first, 'execution.json')
assert first_exec['returncode'] == 1 and first_exec['source_drift'] == []
first_result = read(first, 'pytest-temp/test_visible_rejection_correct0/result.json')
assert first_result['status'] == 'FAIL' and len(first_result['checks']) == 8
worker = read(first, 'pytest-temp/test_visible_rejection_correct0/worker-proof.json')
assert len(worker) == 1 and len(worker[0]['claims']) == 1 and len(worker[0]['wire']) == 1
assert worker[0]['claims'][0]['claimed'] is True
assert worker[0]['claims'][0]['before']['status'] == 'QUEUED'
assert worker[0]['claims'][0]['after']['status'] == 'SUCCEEDED'

execution = read(cont, 'execution.json')
page = read(cont, 'page-result.json')
info = read(cont, 'info.json')
child = execution['same_accepted_run']
parent = execution['parent']
assert execution['status'] == 'PASS' and execution['node_returncode'] == 0
assert execution['source_drift'] == [] and execution['worker_requests'] == 0
assert execution['first_fresh_pytest'] == 'FAIL_RETAINED'
assert execution['real_model_requests'] == 0 and page['status'] == 'PASS'
assert len(page['checks']) == 31 and len(page['actions']) == 52 and len(page['requests']) == 55
assert len(page['static_resource_loads']) == 27 and page['boots'] == 1
assert child == worker[0]['run_id'] == info['expected_child'] and parent == info['run']
views = page['run_views']
assert len(views) == 1 and views[0]['run']['id'] == child
assert views[0]['run']['status'] == 'SUCCEEDED' and views[0]['run']['result_version'] == 2
assert 'PENDING' in views[0]['owner_status']
assert page['final_view']['selected_owner_run'] == child
assert 'ACCEPTED' in page['final_view']['owner_status'] and 'UNKNOWN' in page['final_view']['owner_status']

http = [json.loads(line) for line in (cont/'http.ndjson').read_text().splitlines()]
assert len(http) == len(page['requests'])
for logged, requested in zip(http, page['requests']):
    actual = logged['request']
    assert all(actual.get(k) == requested.get(k) for k in ('method', 'path', 'body', 'headers'))
posts = [x for x in http if x['request']['method'] == 'POST']
assert len(posts) == 2 and all(x['request']['path'].endswith('/spec-owner-review-requests') for x in posts)
assert [x['request']['body']['command'] for x in posts] == ['PREPARE', 'DECIDE']
assert all(x['response']['status'] == 201 for x in posts)
assert not any(x['request']['path'].endswith('/correction-runs') for x in posts)
recovery = [x for x in http if '/correction-requests/' in x['request']['path']]
assert len(recovery) == 1 and recovery[0]['request']['method'] == 'GET' and recovery[0]['response']['status'] == 200
receipt = json.loads(recovery[0]['response']['text'])
assert receipt['request_key'] == info['recovery_key'] and receipt['run_id'] == child and receipt['parent_run_id'] == parent
detail_reads = [json.loads(x['response']['text']) for x in http
    if x['request']['path'].endswith('/runs/'+child) and x['response']['status'] == 200]
assert detail_reads and all(x['id'] == child and x['status'] == 'SUCCEEDED' for x in detail_reads)
owner_reads = [json.loads(x['response']['text']) for x in http
    if x['request']['path'].endswith('/runs/'+child+'/spec-owner-review') and x['response']['status'] == 200]
assert owner_reads and any(x['run_id'] == child and x['sequence'] == 0 and x['owner_acceptance'] == 'PENDING' for x in owner_reads)
for asset in page['static_resource_loads']:
    key = 'src/sim2act/web/' + ('index.html' if asset['path'] == '/' else asset['path'].lstrip('/'))
    assert asset['status'] == 200 and cont_map[key]['sha256'] == asset['sha256'], asset['path']

before = read(cont, 'database-before.json')
after = read(cont, 'database-after.json')
assert set(before) == set(after) and len(before) == 55
changed = [k for k in before if before[k] != after[k]]
assert set(changed) == {'natural_owner_records', 'natural_owner_seals'}
assert all(row in after[t] for t in before for row in before[t])
for t in changed:
    assert len(before[t]) == 2 and len(after[t]) == 4
new_records = [x for x in after['natural_owner_records'] if x not in before['natural_owner_records']]
new_records.sort(key=lambda x:x['sequence'])
new_seals = [x for x in after['natural_owner_seals'] if x not in before['natural_owner_seals']]
assert [x['kind'] for x in new_records] == ['PREPARE', 'DECIDE']
assert [x['status'] for x in new_records] == ['PENDING', 'ACCEPTED']
assert [x['sequence'] for x in new_records] == [1, 2]
assert new_records[1]['previous_fingerprint'] == new_records[0]['fingerprint']
for row, post in zip(new_records, posts):
    assert row['run_id'] == child and row['payload']['request'] == post['request']['body']
    assert row['request_fingerprint'] == fp(post['request']['body'])
    assert row['fingerprint'] == fp(row['payload'])
    metadata = {k:v for k,v in row.items() if k not in {'payload', 'fingerprint'}}
    assert row['payload']['metadata'] == metadata
    seal = next(x for x in new_seals if x['record_id'] == row['id'])
    assert seal['run_id'] == child and seal['payload_fingerprint'] == row['fingerprint']
    assert seal['metadata_fingerprint'] == fp({k:v for k,v in row.items() if k != 'payload'})
    assert json.loads(post['response']['text'])['record']['id'] == row['id']
    assert row['payload']['contract']['run_id'] == child
    assert row['payload']['contract']['result_version'] == 2
    assert row['payload']['contract']['human_correction']['reference']['parent_run_id'] == parent
choices = new_records[1]['payload']['choices']
assert choices and all(x['choice'] == 'ACCEPT' and x['reason'].startswith('SIMULATED') for x in choices)

comparison = read(cont, 'parent-history-comparison.json')
fields = comparison['fields']
assert len(fields) == 11 and comparison['equal'] is True
assert {k:comparison['before'].get(k) for k in fields} == {k:comparison['after'].get(k) for k in fields}
first_http = [json.loads(line) for line in (first/'pytest-temp/test_visible_rejection_correct0/http.ndjson').read_text().splitlines()]
old_parent = next(json.loads(x['response']['text']) for x in first_http
    if x['request']['path'].endswith('/runs/'+parent) and x['response']['status'] == 200)
assert old_parent == comparison['before']
history = read(cont, 'history-proof.json')
assert history['recursive_status'] == 409 and 'Corrections-of-corrections' in json.dumps(history['recursive_response'])
assert history['child_owner']['owner_acceptance'] == 'ACCEPTED'
assert history['child_owner']['run_id'] == child
assert history['old_rows_preserved'] and history['typed_rows_unchanged']

correction = read(cont, 'classification-correction.json')
assert page['classification'] == correction['raw_page_classification']
assert execution['classification'] == correction['actual_classification']
result = dict(status='LIMITED_PASS_FOR_RETAINED_CHAIN_AND_COLD_CONTINUATION',
    method='Pure files and current source bytes; no product execution or DB access',
    manifests=sealed, input_maps=dict(first_entries=len(first_map), continuation_entries=len(cont_map),
        each_before_after_equal=True, product_entries=len(source_keys), product_bytes_equal_across_executions_and_current=True),
    harness_bridges=bridges,
    first_fresh_pytest=dict(status='FAIL_RETAINED', node_id=cases[0].attrib.get('name'),
        junit_seconds=cases[0].attrib['time'], outer_seconds=first_exec['elapsed_seconds'],
        passed_page_checks=8, child_worker_claims=1, retained_child_mock_wire=1, child_status='SUCCEEDED'),
    continuation=dict(status='PASS', seconds=execution['elapsed_seconds'], pytest=False,
        checks=31, actions=52, page_requests=55, get_requests=53, post_requests=2,
        assets=27, boots=1, worker=0, model=0, correction_run_posts=0,
        owner_post_commands=['PREPARE','DECIDE'], child=child, parent=parent,
        recovered_request_key=receipt['request_key'], synthetic_human_acceptance=True,
        raw_metadata_overstatement_preserved=True),
    snapshot_exports=dict(source='Author-produced database-before/after JSON; physical DB not read',
        table_count=55, unchanged_tables=53, changed_tables={t:dict(before=len(before[t]), after=len(after[t])) for t in changed},
        all_old_exported_rows_preserved=True, runs_app_runs_typed_unchanged=True,
        new_owner_records=2, new_owner_seals=2, new_record_fingerprints_and_seals_recomputed=True),
    parent_history=dict(source='Retained first HTTP compared with continuation author GET export',
        fields=fields, equal=True), recursive_rejection=dict(status=409,
            no_write_evidence='Executed author snapshot assertion in retained continuation runner; no separate post-rejection full snapshot retained'),
    limitations=['No successful fresh all-in-one pytest chain; first FAIL is retained',
        'Continuation is not a new pytest or Worker/model execution',
        'Current later readiness/metadata-only harness edits were not rerun as a fresh chain',
        'Historical cancellation/revocation/late cases are not current-source requalifications',
        'Physical DB content/hash, private holdout, Git/auth/network, real model, Windows/native, PG and CI not reviewed by execution',
        'Known revocation-to-stop UI reachability gap is deferred, not fixed here',
        'No future commit/push is endorsed'])
(out/'final-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','input_maps','first_fresh_pytest','continuation','snapshot_exports')},ensure_ascii=False,indent=2))
