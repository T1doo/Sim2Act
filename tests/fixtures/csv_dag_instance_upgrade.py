"""Actual archived executable creates a successful two-step source, not new metadata."""
import hashlib
import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from test_column_patches import setup
from test_csv_dag import NoModel
from test_delivery_graph_apps import snapshot
from sim2act import csv_dag
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker
body=json.load(sys.stdin)
store=Store(body['database_url'],test_only=True)
if body['schema']:store.engine=store.engine.execution_options(schema_translate_map={None:body['schema']})
settings=Settings(body['database_url'],Path(body['data_root']),mode='mock')
client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer synthetic-test-A'
env=(store,settings,client,body['owner'],body['other'],body['project'],body['resource'])
aid,rid,anchor,_,_=setup(env)
base=f"/api/projects/{body['project']}/apps/{aid}/csv-dag"
composition=dict(version='csv.composition.v1',nodes=[
    dict(step_id='read',action='resource.read',depends_on=[],inputs={'resource_id':dict(source='data',ref='source',field='resource_id')}),
    dict(step_id='total',action='data.aggregate_csv',column='amount',depends_on=['read'],inputs={'resource_id':dict(source='step',ref='read',field='resource_id'),'column':dict(source='input',field='total_column')})])
plan=client.post(base,json=dict(expected_candidate_fingerprint=anchor['candidate_fingerprint'],expected_graph_fingerprint=anchor['graph_fingerprint'],column='amount',request_key='old-two-step',composition=composition))
assert plan.status_code==201,plan.text
accepted=client.post(base+'/old-two-step/runs',json=dict(expected_plan_fingerprint=plan.json()['plan_fingerprint'],consent='CONFIRM_EXACT_OFFLINE_CSV_DAG',request_key='old-source'))
assert accepted.status_code==202,accepted.text
w=Worker(store,settings,NoModel());job=store.claim(w.id,settings.lease_seconds);assert job['id']==accepted.json()['run_id'];w.process(job)
proof=client.get('/api/csv-dag/runs/'+job['id']);assert proof.status_code==200 and proof.json()['status']=='SUCCEEDED'
unsupported=client.post('/api/csv-dag/runs/'+job['id']+'/release-approvals',json=dict(expected_plan_fingerprint=plan.json()['plan_fingerprint'],request_key='old-not-supported'))
assert unsupported.status_code==404
Path(body['output']).write_text(json.dumps(dict(old_module_path=csv_dag.__file__,old_module_sha256=hashlib.sha256(Path(csv_dag.__file__).read_bytes()).hexdigest(),app_id=aid,resource_id=rid,base=base,run_id=job['id'],plan=plan.json(),proof=proof.json(),old_snapshot=snapshot(env)),ensure_ascii=False,indent=2)+'\n')
client.close();store.engine.dispose()
