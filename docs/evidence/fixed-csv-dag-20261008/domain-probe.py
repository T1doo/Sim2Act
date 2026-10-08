"""Owned actual API evidence: creation/execution preserves unrelated domain objects."""
import csv
import hashlib
import io
import json
import sys
from fractions import Fraction
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.insert(0, str(Path.cwd() / 'tests'))
from conftest import env

from sim2act.api import create_app
from sim2act.db import Store, meta
from sim2act.worker import Worker

name = sys.argv[1]
root = Path('/tmp/sim2act-dag-domain2-' + name)
root.mkdir()
fixture = env.__wrapped__(root)
e = next(fixture)
store, settings, client, owner, _, pid, _ = e
out = Path('docs/evidence/fixed-csv-dag-20261008')
class NoModel:
    def request(self, *a, **kw):
        raise AssertionError('No model allowed')
def snapshot():
    with store.engine.connect() as c:
        return {t.name: sorted([dict(r) for r in c.execute(select(t)).mappings()], key=lambda r: json.dumps(r,sort_keys=True)) for t in meta.sorted_tables}
def preserve(before, after, allowed):
    names = sorted(set(before) - set(allowed))
    for k in names:
        assert before[k] == after[k], k
    return names
try:
    data = Path('tests/fixtures/column-binding.csv').read_text()
    rows = list(csv.DictReader(io.StringIO(data)))
    totals = {k: str(sum((Fraction(r[k]) for r in rows), Fraction())) for k in ['amount','quantity']}
    assert totals == dict(amount='30',quantity='15')
    rid = client.post(f'/api/projects/{pid}/resources',json=dict(name='owned-dag.csv',format='csv',content=data)).json()['id']
    aid = client.post(f'/api/projects/{pid}/apps/csv-preview',json=dict(name='owned fixed DAG',goal='engineering only',resource_id=rid)).json()['id']
    original = client.post(f'/api/apps/{aid}/previews',json=dict(input=dict(column='amount'),request_key='original')).json()
    assert original['output']['sum'] == totals['amount']
    app = client.get(f'/api/apps/{aid}').json()
    g = client.post(f'/api/projects/{pid}/apps/{aid}/delivery-graph/derive',json=dict(expected_candidate_fingerprint=app['fingerprint'],request_key='original-graph')).json()
    base = f'/api/projects/{pid}/apps/{aid}/csv-dag'
    before = snapshot()
    p = client.post(base,json=dict(expected_candidate_fingerprint=app['fingerprint'],expected_graph_fingerprint=g['graph_fingerprint'],column='quantity',request_key='domain-plan'))
    assert p.status_code == 201, p.text
    plan = p.json()
    after_plan = snapshot()
    plan_kept = preserve(before, after_plan, ['delivery_graph_requests'])
    b = dict(expected_plan_fingerprint=plan['plan_fingerprint'],consent='CONFIRM_EXACT_OFFLINE_CSV_DAG',request_key='domain-run')
    r = client.post(base+'/domain-plan/runs',json=b)
    assert r.status_code == 202, r.text
    accepted = r.json()
    after_run = snapshot()
    run_kept = preserve(after_plan, after_run, ['delivery_graph_requests','runs','run_contracts','events'])
    assert Worker(store,settings,NoModel()).once()
    after_work = snapshot()
    work_kept = preserve(after_run,after_work,['runs','operations','operation_intents','events','heartbeats'])
    cold = Store(settings.database_url,test_only=True)
    if not store.sqlite:
        cold.engine = cold.engine.execution_options(**store.engine.get_execution_options())
    c = TestClient(create_app(cold,settings))
    c.headers['Authorization'] = 'Bearer synthetic-test-A'
    try:
        checked = c.get('/api/csv-dag/runs/'+accepted['run_id'])
        assert checked.status_code == 200, checked.text
        job = checked.json()
        assert job['status'] == 'SUCCEEDED' and job['result']['output']['sum'] == totals['quantity']
        assert job['result']['output']['text'] == '列 quantity；行数 2；合计 15'
        assert c.post(base+'/domain-plan/runs',json=b).json()['run_id'] == accepted['run_id']
        assert c.get(f'/api/apps/{aid}').json()['history'][0] == original
        assert snapshot() == after_work
    finally:
        c.close()
        cold.engine.dispose()
    source = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/sim2act').glob('*.py')}
    value = dict(source_sha='e8b1ed4199a1234060bafbe658cf7a9c52088fff',case_source_hash=hashlib.sha256(data.encode()).hexdigest(),expected=totals,
        original_preview=original,plan=plan,accepted=accepted,cold_read=job,
        unchanged_tables=dict(plan=plan_kept,accept=run_kept,execute=work_kept),
        protected_domain_changes=0,model_requests=0,business_writes=0,source_module_hashes=source,independent_review='NOT_PERFORMED_BY_THIS_AUTHOR')
    (out/(name+'-domain-proof.json')).write_text(json.dumps(value,indent=2))
finally:
    try: next(fixture)
    except StopIteration: pass
