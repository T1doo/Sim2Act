import hashlib, json, socket, threading, time
from pathlib import Path
import httpx, uvicorn
from sqlalchemy import text
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, new_id
root=Path('/tmp/sim2act-control-baseline')
proof=[]
for kind in ('sqlite','pg'):
 url='sqlite:///'+str(root/'fixture.db') if kind=='sqlite' else 'postgresql+psycopg://postgres@/postgres?host=/tmp/sim2act-control-pg/socket'
 store=Store(url,test_only=True);schema=None
 if not store.sqlite:
  schema=new_id('test')
  with store.engine.begin() as c:c.execute(text('CREATE SCHEMA "'+schema+'"'))
  store.engine=store.engine.execution_options(schema_translate_map={None:schema})
 store.initialize(fresh_test_schema=schema)
 store.user('owned baseline fixture','synthetic-control-baseline')
 settings=Settings(url,root,mode='mock')
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 server=uvicorn.Server(uvicorn.Config(create_app(store,settings),host='127.0.0.1',port=port,log_level='error'))
 thread=threading.Thread(target=server.run,daemon=True);thread.start()
 try:
  deadline=time.monotonic()+10
  while not server.started:
   assert thread.is_alive() and time.monotonic()<deadline
   time.sleep(.01)
  with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30,headers={'Authorization':'Bearer synthetic-control-baseline','Connection':'close'}) as c:
   pid=c.post('/api/projects',json={'name':'owned baseline controls'}).json()['id']
   rid=c.post(f'/api/projects/{pid}/resources',json=dict(name='owned.csv',format='csv',content='item,amount,quantity\nA,10,7\nB,20,8\n')).json()['id']
   aid=c.post(f'/api/projects/{pid}/apps/csv-preview',json=dict(name='owned app',goal='engineering only',resource_id=rid)).json()['id']
   app=c.get(f'/api/apps/{aid}').json();base=f'/api/projects/{pid}/apps/{aid}/delivery-graph'
   anchor=c.post(base+'/derive',json=dict(expected_candidate_fingerprint=app['fingerprint'],request_key='baseline')).json()
   node=next(n for n in anchor['graph']['nodes'] if n['key']=='action:aggregate')
   defined=c.post(base+'/column-patches',json=dict(expected_candidate_fingerprint=app['fingerprint'],expected_graph_fingerprint=anchor['graph_fingerprint'],request_key='safe',kind='csv.column-binding.v1',baseline_column='amount',column='quantity',change=dict(node_id=node['id'],expected_revision=node['revision'],expected_content_fingerprint=node['content_fingerprint'])))
   assert defined.status_code==201
   fp=defined.json()['patch_fingerprint']
   check=c.post(base+'/column-patches/safe/checks',json=dict(expected_patch_fingerprint=fp,request_key='nul\0check'))
   path=c.post(base+'/column-patches/nul%00path/checks',json=dict(expected_patch_fingerprint=fp,request_key='safe-check'))
   wanted=(201,409) if kind=='sqlite' else (500,500)
   assert (check.status_code,path.status_code)==wanted,(kind,check.text,path.text)
   proof.append(dict(environment=kind,transport='actual loopback HTTP',definition_status=201,json_nul_check_status=check.status_code,encoded_nul_path_status=path.status_code))
 finally:
  server.should_exit=True;thread.join(10);assert not thread.is_alive()
  if schema:
   with store.engine.begin() as c:c.execute(text('DROP SCHEMA "'+schema+'" CASCADE'))
  store.engine.dispose()
result=dict(source_sha='eb2e5fbe72ac8585a65c441eaff5e02dd50825a5',loaded_column_module_sha256=hashlib.sha256((root/'src/sim2act/column_patches.py').read_bytes()).hexdigest(),cases=proof,live=0)
Path('docs/evidence/column-patch-control-fix-20261008/baseline-reproduction.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
