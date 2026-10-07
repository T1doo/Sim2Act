from pathlib import Path
import importlib.util,json,sys
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sim2act.api import create_app
from sim2act.db import attempts,runs

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
protocol=load('owned_protocol','scripts/protocol-ui/fixture.py')
sys.path.insert(0,str(Path('scripts/conditional-ui').resolve()))
control=load('owned_control','scripts/conditional-ui/fixture.py')
p=Path('/tmp/bounded-native-final-review') / ('repair-optimized-fixture' if sys.flags.optimize else 'repair-normal-fixture');protocol.seed(p,12345);info=json.loads((p/'info.json').read_text());store,settings=protocol.context(p)
with TestClient(create_app(store,settings),headers={'Authorization':'Bearer '+info['bearer']}) as client:
 public=next(x for x in client.get('/api/projects/'+info['project']+'/protocol/contracts').json()['items'] if x['contract_id']==info['source_contract'])
 made=client.post('/api/projects/'+info['project']+'/protocol/source',json={'contract_id':public['contract_id'],'goal':public['public_goal'],'inputs':public['public_inputs'],'resource_ids':[info['source']],'request_key':'independent-old-namespace'})
 if made.status_code != 202: raise RuntimeError('Actual enqueue failed:'+made.text)
 rid=made.json()['run_id']
 before=control.action(p,'snapshot')
 try: outcome={'reply':control.action(p,'run-source'),'error':None}
 except Exception as e: outcome={'reply':None,'error':type(e).__name__+': '+str(e)}
 after=control.action(p,'snapshot')
 with store.tx() as c:
  current=dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one())
 result={'source':'1f96d887e9f9ca06b506afa319892fb220f67c35','queued_via_actual_http':'original protocol/source; not conditional-runs','created_http':made.status_code,'run_id':rid,'outcome':outcome,'before_attempts':before['attempts_count'],'after_attempts':after['attempts_count'],'before_table_run_fp':before['tables']['runs'],'after_table_run_fp':after['tables']['runs'],'current_run_status':current['status'],'current_run_error':current['error'],'before_snapshot':before,'after_snapshot':after}
 (Path('/tmp/bounded-native-final-review') / ('repair-optimized-result.json' if sys.flags.optimize else 'repair-normal-result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
store.engine.dispose()
if outcome['reply'] is not None or outcome['error'] is None or before != after or current['status'] != 'QUEUED': raise RuntimeError('Repair source refusal not clean')
