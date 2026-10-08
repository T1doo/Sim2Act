import importlib.util,json
from pathlib import Path
from sqlalchemy import select,update
from fastapi.testclient import TestClient
from sim2act.db import runs,meta,fingerprint
from sim2act.errors import DomainError
from sim2act.natural_activations import now
spec=importlib.util.spec_from_file_location('demo','scripts/natural_activation_demo.py');demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
def snapshot(store):
 with store.tx() as c:return fingerprint({t.name:[dict(r) for r in c.execute(select(t)).mappings()] for t in meta.sorted_tables})
with demo.demo() as f,TestClient(f['app']) as c:
 c.headers['Authorization']='Bearer '+demo.PUBLIC_FIXTURE_TOKEN
 card=f['cards']['sum_quantity_z'];rid=c.post('/api/natural-activations/'+f['session']['id']+'/goal-cards/'+card['id']+'/planned-runs',json={'expected_version':card['version'],'expected_fingerprint':card['fingerprint'],'request_key':'probe-old'}).json()['run_id']
 assert f['worker'].once();view=c.get('/api/runs/'+rid).json()
 assert c.post('/api/runs/'+rid+'/confirm-natural-plan',json={'expected_version':view['version'],'expected_plan_fingerprint':view['natural_plan']['fingerprint'],'request_key':'probe-confirm'}).status_code==200
 assert f['worker'].once();view=c.get('/api/runs/'+rid).json();assert view['status']=='PARTIAL'
 with f['store'].tx() as tx:
  row=tx.execute(select(runs).where(runs.c.id==rid)).mappings().one()
  tx.execute(update(runs).where(runs.c.id==rid).values(status='RUNNING',lease_until=now()+30))
 before=snapshot(f['store']);results=[]
 for result in [None,view['result']]:
  try:f['worker'].finish(rid,row['fence'],'SUCCEEDED',result=result,verify_goal_source=False)
  except DomainError as e:results.append({'result':'missing' if result is None else 'legacy_not_run','optional_flag':False,'code':e.code})
  else:raise AssertionError('Legacy default finish falsely succeeded')
  assert snapshot(f['store'])==before
 assert len(results)==2
 root=f['root']
assert not root.exists()
Path('/tmp/sim2act-fixed-goal/default-finalization-results.json').write_text(json.dumps({'execution_sha':'ed48426ac6ce20b21135c8d8bb0c73729d5fd503','checks':results,'all_table_fingerprint_unchanged':True,'owned_fixture_removed':True,'real_provider_calls':0},indent=2)+'\n')
print('2 default-finalization negative checks PASS; tables unchanged; owned fixture removed')
