import hashlib
import json
import sqlite3
import subprocess
import zipfile
from pathlib import Path

root = Path('/workspace/pa-use-running-clean-install')
unpack = root / 'Sim2Act-local-candidate'
data = unpack / 'synthetic-pa-demo'
commit = 'fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675'
repo = Path('/workspace/Sim2Act')
def read(path):
    return json.loads(path.read_text())
def blob(commit, name):
    return subprocess.check_output(['git', 'show', commit + ':' + name], cwd=repo)
receipt = read(data / 'demo-receipt.json')
workers = read(data / 'worker-receipts.json')
mocks = read(data / 'mock-receipts.json')
http = read(data / 'http-receipts.json')
origin = read(root / 'runtime-origin.json')
fixtures = read(unpack / 'scripts/local-candidate/mock-fixtures.json')
oldfixtures = json.loads(blob('0f0819a6a481841a0221cc69f75959326f264529', 'scripts/local-candidate/mock-fixtures.json'))
assert receipt['status'] == 'PASS' and receipt['scenario'] == 'PA_NEW_MATERIAL_TWICE'
assert receipt['worker_claims'] == workers
assert len(workers) == 4 and [x['status'] for x in workers] == ['SUCCEEDED', 'PARTIAL', 'SUCCEEDED', 'SUCCEEDED']
assert all(x['claim_count'] == x['fence'] == x['service_turns'] == 1 for x in workers)
assert all([e['kind'] for e in x['service_ledger']] == ['CLAIMED'] for x in workers)
assert all({e['run_id'] for e in x['service_all_claims']} == {x['run_id']} for x in workers)
assert len(mocks) == 5 and [x['stage'] for x in mocks] == ['generation'] * 3 + ['pa'] * 2
assert all(x['transport'] == 'httpx.MockTransport' for x in mocks)
assert receipt['real_model_requests'] == 0 and receipt['formal_publication_enabled'] is False
assert receipt['pa_new_material_per_use'] == 'PASS_TWO_ACTUAL_RUNS_V1_V2'
assert all(receipt[k]['submission'] == 'EXPLICIT_NEW_MATERIAL_GOAL_PER_USE_REVIEW' for k in ['natural_pa_previous', 'natural_pa'])
assert receipt['natural_pa_previous']['app_id'] == receipt['natural_pa']['app_id']
assert receipt['natural_pa_previous']['instance_id'] == receipt['natural_pa']['instance_id']
assert [receipt[k]['result_version'] for k in ['natural_pa_previous', 'natural_pa']] == [1, 2]
assert len([x for x in http if x['path'].endswith('/pa-use-reviews')]) == 2
assert len([x for x in http if x['path'].endswith('/pa-use-runs')]) == 4
assert not any('/pb-use-' in x['path'] or '/extraction' in x['path'] for x in http)
assert all(x['status'] in [200, 201, 202] for x in http)
assert fixtures['recipe'] == oldfixtures['recipe']
assert fixtures['materials']['source'] == oldfixtures['materials']['source']
assert fixtures['materials']['pa_use'] == oldfixtures['materials']['pa_use']
assert fixtures['materials']['pb_use'] == oldfixtures['materials']['pb_use']
assert origin['source_commit'] == commit and origin['fresh_venv'] and origin['imported_from_installed_wheel'] and not origin['checkout_src_on_sys_path']
site = unpack / '.venv/lib/python3.12/site-packages'
with zipfile.ZipFile(unpack / 'wheels/sim2act-0.1.0-py3-none-any.whl') as z:
    files = {x for x in z.namelist() if x.startswith('sim2act/')}
    for name in files:
        assert (site / name).read_bytes() == z.read(name)
    installed = {str(p.relative_to(site)) for p in (site / 'sim2act').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert installed == files and len(files) == 113
for name in ['scripts/local_candidate_demo.py', 'scripts/local-candidate/mock-fixtures.json']:
    assert (unpack / name).read_bytes() == blob(commit, name)
oldproof = read(Path('/workspace/local-candidate-clean-install/failed-pa-run-readonly.json'))
oldgoal = oldproof['internal_run_bindings'][0]['snapshot']['spec_goal']['snapshot']['content']
def normalize_goal(value):
    value = dict(value)
    value['resource_refs'] = ['EXACT_REBOUND_MATERIAL_ID']
    return value
summaries, pa_details, turn_proofs = [], [], []
db = data / 'synthetic-demo.db'
before = hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as c:
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    assert c.execute('SELECT count(*) FROM runs').fetchone()[0] == 4
    for index, item in enumerate(workers):
        row = dict(c.execute('SELECT id,status,fence,worker_id,created_at FROM runs WHERE id=?', (item['run_id'],)).fetchone())
        assert row['status'] == item['status'] and row['fence'] == 1 and row['worker_id'] == item['service_worker_id']
        count = c.execute('SELECT count(*) FROM events WHERE run_id=? AND kind=?', (row['id'], 'CLAIMED')).fetchone()[0]
        recoveries = c.execute('SELECT count(*) FROM events WHERE run_id=? AND kind IN (?,?)', (row['id'], 'WORKER_LOST', 'RECONCILED')).fetchone()[0]
        assert count == 1 and recoveries == 0
        attempts = [dict(r) for r in c.execute('SELECT mode,status,request_model,response_model FROM attempts WHERE run_id=? ORDER BY created_at', (row['id'],))]
        assert len(attempts) == [0, 3, 1, 1][index]
        assert all(x['mode'] == 'MOCK' and x['status'] == ('RECEIVED' if index == 1 else 'VERIFIED') and x['request_model'] == x['response_model'] == 'intern-s2' for x in attempts)
        turns = read(data / ('worker-service-' + row['id'] + '.json'))
        assert len(turns) == 1 and turns[0]['claimed_work'] is True
        assert turns[0]['before']['status'] == 'QUEUED' and turns[0]['after']['status'] == row['status']
        assert turns[0]['before']['created_at'] == turns[0]['after']['created_at'] == row['created_at']
        assert turns[0]['before']['deadline'] == turns[0]['after']['deadline'] == row['created_at'] + 300
        assert turns[0]['finished_at'] < turns[0]['after']['deadline']
        assert not turns[0]['before']['unexpected_active_run_ids'] and not turns[0]['after']['unexpected_active_run_ids']
        summaries.append({'run_id': row['id'], 'status': row['status'], 'claim_count': 1, 'fence': 1, 'service_turns': 1, 'recovery_events': 0, 'model_attempts': len(attempts), 'attempt_modes': sorted({x['mode'] for x in attempts})})
        turn_proofs.append({'run_id': row['id'], 'service_wall_seconds': turns[0]['finished_at'] - turns[0]['started_at'], 'original_deadline_preserved': True, 'finished_before_original_deadline': True})
    for index, (key, material) in enumerate([('natural_pa_previous', 'pa_use'), ('natural_pa', 'pb_use')]):
        result = receipt[key]
        binding = dict(c.execute('SELECT app_run_id,snapshot FROM internal_run_bindings WHERE run_id=?', (result['run_id'],)).fetchone())
        snapshot = json.loads(binding['snapshot'])
        use = snapshot['pa_use']['review']
        assert snapshot['pa_base_data_version'] == index
        assert use['request_key'] == ['mock-pa-use', 'mock-pa-use-second'][index]
        assert snapshot['instance_id'] == result['instance_id']
        assert snapshot['natural_spec_clock'] == {'created_at': workers[index + 2]['last_observation']['created_at'], 'deadline': workers[index + 2]['last_observation']['deadline']}
        resource = dict(c.execute('SELECT id,content,hash,format FROM resources WHERE id=?', (use['resource_id'],)).fetchone())
        fixed = oldfixtures['materials'][material]
        assert resource['content'] == fixed['content'] and resource['format'] == 'txt'
        assert resource['hash'] == use['expected_source_hash'] == hashlib.sha256(fixed['content'].encode()).hexdigest()
        goal = snapshot['spec_goal']
        expected_goal = dict(oldgoal, title='MOCK ' + material)
        assert normalize_goal(goal['snapshot']['content']) == normalize_goal(expected_goal)
        assert goal['card_id'] == use['card_id'] and goal['version'] == use['expected_goal_version'] == 1 and goal['fingerprint'] == use['expected_goal_fingerprint']
        assert goal['snapshot']['content']['resource_refs'] == [resource['id']]
        app_run = dict(c.execute('SELECT * FROM internal_app_runs WHERE id=?', (binding['app_run_id'],)).fetchone())
        assert app_run['status'] == 'SUCCEEDED' and app_run['result_version'] == index + 1
        artifact_rows = c.execute('SELECT id,content FROM resources WHERE hash=?', (result['artifact_sha256'],)).fetchall()
        assert len(artifact_rows) == 1
        artifact = json.loads(artifact_rows[0]['content'])
        assert artifact['source_content'] == resource['content'] and artifact['owner_acceptance'] == 'PENDING' and artifact['semantic_goal_acceptance'] == 'NOT_RUN'
        assert hashlib.sha256(artifact_rows[0]['content'].encode()).hexdigest() == result['artifact_sha256']
        pa_details.append({'run_id': result['run_id'], 'app_id': result['app_id'], 'release_id': snapshot['release_id'], 'instance_id': result['instance_id'], 'base_data_version': snapshot['pa_base_data_version'], 'result_version': index + 1, 'material_key': material, 'source_hash': resource['hash'], 'fixed_0f_material_and_goal_content_match': True, 'goal_version': 1, 'artifact_hash_matches_receipt': True})
    assert pa_details[0]['release_id'] == pa_details[1]['release_id']
    candidate = json.loads(c.execute('SELECT candidate FROM app_drafts WHERE id=?', (receipt['natural_pa']['app_id'],)).fetchone()[0])
    assert candidate['spec_recipe'] == oldfixtures['recipe']
    rows = [dict(r) for r in c.execute('SELECT * FROM internal_instance_data WHERE instance_id=? ORDER BY version', (receipt['natural_pa']['instance_id'],))]
    for row in rows:
        row['data'] = json.loads(row['data'])
    history = [dict(version=row['version'], fingerprint=row['fingerprint'], row_sha256=hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()) for row in rows]
    assert history == receipt['natural_pa_history'] and [row['version'] for row in rows] == [1, 2]
assert hashlib.sha256(db.read_bytes()).hexdigest() == before
preservation = read(Path('/workspace/pa-use-running-investigation-20261016/old-failure-preservation.json'))
assert preservation['db_hash_before'] == preservation['db_hash_after'] == 'bf2293cb3d5f96d9a054596d7e1cccd9905e1088f69620e9fc4e2989375b1d4c'
old_db = Path('/workspace/local-candidate-clean-install/Sim2Act-local-candidate/synthetic-demo/synthetic-demo.db')
assert hashlib.sha256(old_db.read_bytes()).hexdigest() == preservation['db_hash_after']
paths = [data / name for name in ['demo-receipt.json', 'worker-receipts.json', 'mock-receipts.json', 'http-receipts.json']] + sorted(data.glob('worker-service-*.json')) + [root / 'prepare-pa.log', root / 'runtime-origin.json', Path('/workspace/pa-use-running-investigation-20261016/old-failure-preservation.json')]
cold = read(data / 'cold-read-receipt.json') if (data / 'cold-read-receipt.json').exists() else None
if cold:
    assert cold['status'] == 'PASS' and cold['persisted_rows_unchanged'] and cold['cold_process'] and cold['existing_results'] == 3 and cold['workers_started'] == cold['model_requests'] == 0
    paths += [data / 'cold-read-receipt.json', root / 'verify-pa.log']
proof = {'source_commit': commit, 'scenario': receipt['scenario'], 'root_prepare_pa_receipts_verified': True, 'installed_product_files_independently_compared': len(files), 'unpacked_script_fixtures_equal_git': True, 'run_summaries': summaries, 'service_turns': turn_proofs, 'pa_details': pa_details, 'same_app_release_instance': True, 'typed_history_row_hashes_match_receipt': history, 'artifact_hashes_preserved': True, 'five_mock_responses_real_zero': True, 'no_actual_reclaim_or_recovery': True, 'independent_readonly_db_hash_before_after': before, 'old_failure_db_still_original_hash': preservation['db_hash_after'], 'root_old_five_table_preservation_receipt_verified': True, 'root_cold_verify_receipt': cold or 'PENDING at this read', 'reviewer_execution': 'read-only file/receipt comparisons and sqlite mode=ro queries; no Worker, model, new natural fixture or old replay', 'raw_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out = Path('/tmp/f2-pa-service-fc69-actual-receipt-independent-proof.json')
out.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
