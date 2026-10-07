from pathlib import Path
import importlib.util,json,sys
from fastapi.testclient import TestClient
from sim2act.api import create_app

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
protocol=load('probe_protocol','scripts/protocol-ui/fixture.py');sys.path.insert(0,str(Path('scripts/conditional-ui').resolve()));control=load('probe_control','scripts/conditional-ui/fixture.py')
p=Path('/tmp/bounded-native-final-review')/('fifo-optimized-fixture' if sys.flags.optimize else 'fifo-normal-fixture');protocol.seed(p,12345);info=json.loads((p/'info.json').read_text());store,settings=protocol.context(p)
try:
 with TestClient(create_app(store,settings),headers={'Authorization':'Bearer '+info['bearer']}) as client:
  other=info['other_project'];public=next(x for x in client.get('/api/projects/'+other+'/protocol/contracts').json()['items'] if x['contract_id']==info['source_contract']);resource=client.get('/api/projects/'+other+'/resources').json()[0]['id']
  first=client.post('/api/projects/'+other+'/protocol/source',json={'contract_id':public['contract_id'],'goal':public['public_goal'],'inputs':public['public_inputs'],'resource_ids':[resource],'request_key':'fifo-foreign-first'})
  public=client.get('/api/projects/'+info['project']+'/conditional-runs/contract').json()
  second=client.post('/api/projects/'+info['project']+'/conditional-runs/source',json={'resource_id':info['source'],'expected_source_hash':public['source_hash'],'expected_contract_fingerprint':public['check_contract_fingerprint'],'goal':public['goal'],'scenario':{'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':680,'receipt_present':True,'approved':False,'elapsed_days':2},'request_key':'fifo-owned-second'})
  if first.status_code!=202 or second.status_code!=202:raise RuntimeError('Actual fixture HTTP enqueue failure')
  before=control.action(p,'snapshot')
  try: control.action(p,'run-source')
  except ValueError as e: refused=str(e)
  else:raise RuntimeError('Controller skipped earlier foreign project')
  after=control.action(p,'snapshot')
  if before!=after:raise RuntimeError('FIFO refusal changed persistence')
  result={'requested_source':'1f96d887e9f9ca06b506afa319892fb220f67c35','optimized':sys.flags.optimize,'actualHTTPqueued_foreign_then_owned':True,'refused':refused,'before':before,'after':after,'all_tables_unchanged':True,'attempts_delta':after['attempts_count']-before['attempts_count']}
  (Path('/tmp/bounded-native-final-review')/('fifo-optimized-result.json' if sys.flags.optimize else 'fifo-normal-result.json')).write_text(json.dumps(result,indent=2)+'\n')
finally: store.engine.dispose()
