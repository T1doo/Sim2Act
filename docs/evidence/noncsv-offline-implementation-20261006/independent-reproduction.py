"""Independent final assertions using disposable SQLite and frozen manual gold; 0 LIVE."""
import json,hashlib,tempfile,copy
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import update,select,func
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,spec_checklist_tasks,fingerprint,resources,grants
from sim2act.spec_checklists import CHECK,source_checklist,verify_candidate
from sim2act.errors import DomainError
p=Path(__file__).resolve().parent;gold=json.loads((p/'independent-gold.json').read_text());raw=(p/'independent-fixture.md').read_bytes();rid='res_'+'a'*32
candidate={'check_version':CHECK,'source':{'resource_id':rid,'hash':gold['source']['sha256'],'document_id':gold['document_id'],'document_version':gold['document_version'],'coordinate_space':'whole_resource','line_start':1,'line_end':6},'rules':gold['rules']}
source={'resource_id':rid,'hash':hashlib.sha256(raw).hexdigest(),'content':raw.decode(),'format':'md'}
assert source_checklist(source)==candidate
changed=copy.deepcopy(candidate);changed['rules'][0]['quote']='old mutually agreed fake gold'
try:verify_candidate(source,json.dumps(changed))
except DomainError:pass
else:raise AssertionError('fake quote passed')
print('manual gold parser match / synchronized fake quote rejected: PASS')
with tempfile.TemporaryDirectory(prefix='independent-spec-review-') as root:
 store=Store('sqlite:///'+root+'/fixture.db',test_only=True);store.initialize();owner=store.user('synthetic reviewer','synthetic-independent');settings=Settings('sqlite:///'+root+'/fixture.db',Path(root),mode='mock');client=TestClient(create_app(store,settings),raise_server_exceptions=False);client.headers['Authorization']='Bearer synthetic-independent';pid=client.post('/api/projects',json={'name':'synthetic reviewer'}).json()['id'];resource=client.post(f'/api/projects/{pid}/resources',json={'name':'manual.md','format':'md','content':raw.decode()}).json()['id'];candidate['source']['resource_id']=resource
 body={'resource_id':resource,'expected_source_hash':source['hash'],'candidate_json':json.dumps(candidate),'request_key':'manual','synthetic_fixture':True};accepted=client.post(f'/api/projects/{pid}/spec-checklist-tasks',json=body);assert accepted.status_code==201 and accepted.json()['status']=='SUCCEEDED';task=accepted.json();tid=task['id']
 def count():
  with store.tx() as c:return tuple(c.execute(select(func.count()).select_from(t)).scalar_one() for t in [resources,grants,spec_checklist_tasks])
 before=count()
 with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(output={}))
 got=client.get('/api/spec-checklist-tasks/'+tid);replay=client.post(f'/api/projects/{pid}/spec-checklist-tasks',json=body);print('malformed saved output {} HTTP GET/replay',got.status_code,replay.status_code);assert got.status_code==400 and replay.status_code==400;assert count()==before
 with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(output=task['output']))
 bad=copy.deepcopy(body);bad['candidate_json']=1
 with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(request=bad,request_fingerprint=fingerprint(bad)))
 got=client.get('/api/spec-checklist-tasks/'+tid);print('malformed stored candidate_json integer coherent request_fp HTTP GET',got.status_code);assert got.status_code==409;assert count()==before
 bad=copy.deepcopy(body);bad['synthetic_fixture']=1
 with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(request=bad,request_fingerprint=fingerprint(bad)))
 got=client.get('/api/spec-checklist-tasks/'+tid);print('stored synthetic_fixture integer1 coherent request_fp HTTP GET',got.status_code);assert got.status_code==409;assert count()==before
 rejected=client.post(f'/api/projects/{pid}/spec-checklist-tasks',json={**body,'synthetic_fixture':1});assert rejected.status_code==422 and count()==before;print('public POST integer1 HTTP422 / no persistence: PASS')
 with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(request=body,request_fingerprint=fingerprint(body)))
 for label,values in [('proof_list',{'proof':[]}),('receipt_list',{'receipt':[]}),('coherent_proof_source_hash',{'proof':{**task['proof'],'source_hash':'0'*64},'proof_fingerprint':fingerprint({**task['proof'],'source_hash':'0'*64})})]:
  with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(proof=task['proof'],receipt=task['receipt'],proof_fingerprint=task['proof_fingerprint'],**{}))
  with store.tx() as c:c.execute(update(spec_checklist_tasks).where(spec_checklist_tasks.c.id==tid).values(**values))
  got=client.get('/api/spec-checklist-tasks/'+tid);assert got.status_code==400 and count()==before;print(label+' GET400 / no persistence: PASS')
 client.close();store.engine.dispose()
print('review external requests 0; own disposable SQLite only')
