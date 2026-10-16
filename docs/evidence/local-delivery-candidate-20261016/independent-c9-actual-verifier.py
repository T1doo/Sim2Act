import hashlib
import json
import sqlite3
import subprocess
import zipfile
from pathlib import Path

root = Path('/workspace/local-candidate-clean-install-v2')
unpack = root / 'Sim2Act-local-candidate'
data = unpack / 'synthetic-demo'
def read(path):
    return json.loads(path.read_text())
receipt = read(data / 'demo-receipt.json')
workers = read(data / 'worker-receipts.json')
mocks = read(data / 'mock-receipts.json')
cold = read(data / 'cold-read-receipt.json')
http = read(data / 'http-receipts.json')
origin = read(root / 'runtime-origin.json')
serve = read(root / 'serve-smoke.json')
commit = 'c9e9f3fc9787350d1e7997860234694b270a6a7f'
assert receipt['status'] == 'PASS' and workers == receipt['worker_claims']
assert len(workers) == 4 and [x['status'] for x in workers] == ['SUCCEEDED', 'PARTIAL', 'SUCCEEDED', 'SUCCEEDED']
assert all(x['claim_count'] == x['fence'] == 1 for x in workers)
assert len(mocks) == 5 and [x['stage'] for x in mocks] == ['generation'] * 3 + ['pa', 'pb']
assert all(x['transport'] == 'httpx.MockTransport' for x in mocks)
assert receipt['real_model_requests'] == 0 and receipt['formal_publication_enabled'] is False
assert receipt['pa_new_material_per_use'] == 'NOT_RUN_IN_THIS_CANDIDATE'
assert receipt['natural_pa']['submission'] == 'ORIGINAL_SAVED_MATERIAL_AND_GOAL'
assert receipt['natural_pb']['submission'] == 'EXPLICIT_NEW_MATERIAL_GOAL_PER_USE_REVIEW'
assert all(receipt[k]['result_version'] == 1 and receipt[k]['owner_acceptance'] == 'PENDING' and receipt[k]['semantic_acceptance'] == 'NOT_RUN' for k in ['natural_pa', 'natural_pb'])
assert cold['status'] == 'PASS' and cold['persisted_rows_unchanged'] and cold['cold_process'] and cold['workers_started'] == cold['model_requests'] == 0 and cold['existing_results'] == 3
assert len(http) == 46 and all(x['status'] in [200, 201, 202] for x in http)
assert not any('/pa-use-' in x['path'] for x in http)
assert len([x for x in http if x['path'].endswith('/pb-use-runs')]) == 2
assert origin['source_commit'] == commit and origin['fresh_venv'] and origin['imported_from_installed_wheel'] and not origin['checkout_src_on_sys_path']
site = unpack / '.venv/lib/python3.12/site-packages'
wheel = unpack / 'wheels/sim2act-0.1.0-py3-none-any.whl'
with zipfile.ZipFile(wheel) as z:
    files = {x for x in z.namelist() if x.startswith('sim2act/')}
    for name in files:
        assert (site / name).read_bytes() == z.read(name)
    installed = {str(p.relative_to(site)) for p in (site / 'sim2act').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert installed == files
assert len(files) == 113
for name in ['scripts/local_candidate_demo.py', 'scripts/local-candidate/mock-fixtures.json']:
    assert (unpack / name).read_bytes() == subprocess.check_output(['git', 'show', commit + ':' + name], cwd='/workspace/Sim2Act')
assert serve['source_commit'] == commit and serve['status'] == 'PASS' and serve['owned_serve_exit_code'] == 0 and serve['workers_started'] == serve['real_model_requests'] == 0 and serve['native_browser'] == 'NOT_RUN'
assert len(serve['http']) == 9 and [x['status'] for x in serve['http']] == [200] * 8 + [405]
db = data / 'synthetic-demo.db'
before = hashlib.sha256(db.read_bytes()).hexdigest()
summaries, artifacts = [], []
with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as c:
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    for index, item in enumerate(workers):
        run = dict(c.execute('SELECT id,status,fence,worker_id FROM runs WHERE id=?', (item['run_id'],)).fetchone())
        assert run['status'] == item['status'] and run['fence'] == item['fence'] and run['worker_id'] == item['worker_id']
        claim = c.execute('SELECT count(*) FROM events WHERE run_id=? AND kind=?', (item['run_id'], 'CLAIMED')).fetchone()[0]
        assert claim == 1
        attempts = [dict(r) for r in c.execute('SELECT mode,status,request_model,response_model FROM attempts WHERE run_id=? ORDER BY created_at', (item['run_id'],))]
        expected_attempt_status = 'RECEIVED' if index == 1 else 'VERIFIED'
        assert all(x['mode'] == 'MOCK' and x['status'] == expected_attempt_status and x['request_model'] == x['response_model'] == 'intern-s2' for x in attempts)
        summaries.append({'run_id': run['id'], 'status': run['status'], 'fence': run['fence'], 'claim_count': claim, 'attempt_count': len(attempts), 'attempt_modes': sorted({x['mode'] for x in attempts}), 'attempt_statuses': sorted({x['status'] for x in attempts})})
    assert [x['attempt_count'] for x in summaries] == [0, 3, 1, 1]
    for k in ['deterministic', 'natural_pa', 'natural_pb']:
        result = receipt[k]
        row = c.execute('SELECT a.status,a.result_version FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?', (result['run_id'],)).fetchone()
        assert row['status'] == 'SUCCEEDED' and row['result_version'] == result['result_version'] == 1
    for k in ['natural_pa', 'natural_pb']:
        result = receipt[k]
        typed = c.execute('SELECT version FROM internal_instance_data WHERE instance_id=?', (result['instance_id'],)).fetchall()
        assert [x[0] for x in typed] == [1]
        rows = c.execute('SELECT id,content FROM resources WHERE hash=?', (result['artifact_sha256'],)).fetchall()
        assert len(rows) == 1
        content = rows[0]['content']
        assert hashlib.sha256(content.encode()).hexdigest() == result['artifact_sha256']
        artifact = json.loads(content)
        assert artifact['owner_acceptance'] == 'PENDING' and artifact['semantic_goal_acceptance'] == 'NOT_RUN'
        artifacts.append({'family': k, 'result_version': 1, 'artifact_hash_matches_receipt': True, 'owner_acceptance': 'PENDING', 'semantic_goal_acceptance': 'NOT_RUN'})
after = hashlib.sha256(db.read_bytes()).hexdigest()
assert before == after
paths = [data / f for f in ['demo-receipt.json', 'worker-receipts.json', 'mock-receipts.json', 'http-receipts.json', 'cold-read-receipt.json']] + [root / f for f in ['demo-prepare.log', 'demo-verify.log', 'runtime-origin.json', 'pip-check.log', 'serve-smoke.json', 'serve-smoke.log', 'serve.log']]
proof = {'source_commit': commit, 'root_actual_complete_chain_receipts_verified': True, 'installed_product_files_independently_compared_to_wheel': len(files), 'unpacked_demo_script_and_fixtures_equal_git_freeze': True, 'http_prepare_receipts': len(http), 'worker_runs': summaries, 'artifacts': artifacts, 'mock_response_count': len(mocks), 'real_model_requests': 0, 'cold_read_receipt_existing_results': cold['existing_results'], 'cold_read_reports_all_persisted_rows_unchanged': True, 'independent_readonly_db_hash_before': before, 'independent_readonly_db_hash_after': after, 'serve_get_receipts': 8, 'serve_post405': True, 'owned_serve_exit_code': 0, 'pa_new_material_per_use': 'NOT_RUN_IN_THIS_CANDIDATE', 'old_0f_complete_chain': 'FAIL retained, no replay', 'execution_scope': 'receipt/file comparison + sqlite mode=ro queries only; no importing product, no Worker or model rerun', 'first_probe_assertion_correction': 'Incorrectly expected Attempt SUCCEEDED; actual existing contract is generation RECEIVED, runtime VERIFIED. Reviewer probe correction, not a product failure.', 'raw_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p = Path('/tmp/f2-local-candidate-c9-actual-receipt-independent-proof.json')
p.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
