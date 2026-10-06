import sys,tempfile,pathlib,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
import conftest
from test_internal_api import release,instance,enqueue,path
from test_persistent_app_runs import NoModel
from sim2act.worker import Worker
from sim2act.db import internal_run_bindings,grants,internal_app_runs,app_drafts
from sqlalchemy import select,update
root=pathlib.Path(tempfile.mkdtemp(prefix='e20-review-'));fixture=conftest.env.__wrapped__(root);env=next(fixture)
try:
 store,s,client,A,B,pid,rid=env
 ra,aid,fp=release(env);ia=instance(env,ra);ia2=instance(env,ra,key='second');ja=enqueue(env,ia,ra).json();assert Worker(store,s,NoModel()).once();assert client.get(path(ia,ja)).json()['result']['sum']=='4.00'
 queued=enqueue(env,ia,ra,key='stop-after-revoke').json()
 # Independent principal/project/result, using only newly synthesized authorized fixtures.
 client.headers.update({'Authorization':'Bearer synthetic-test-B'});pb=client.post('/api/projects',json={'name':'synthetic foreign B'}).json()['id'];rbid=client.post(f'/api/projects/{pb}/resources',json={'name':'private.csv','format':'csv','content':'amount\n321.99\n'}).json()['id'];envB=(store,s,client,B,A,pb,rbid);rb,bid,bfp=release(envB);ib=instance(envB,rb);jb=enqueue(envB,ib,rb).json()
 # Worker will safely process queued A first then B.
 assert Worker(store,s,NoModel()).once();assert Worker(store,s,NoModel()).once();assert client.get(path(ib,jb)).json()['result']['sum']=='321.99'
 client.headers.update({'Authorization':'Bearer synthetic-test-A'})
 for url in [f'/api/internal/instances/{ib["id"]}',path(ib,jb),path(ib,jb)+'/control-status',path(ia2,ja),path(ia2,ja)+'/control-status']:
  response=client.get(url);assert response.status_code==403,(url,response.text);assert '321.99' not in response.text and '4.00' not in response.text
 print('cross-owner/cross-instance history and control rejects PASS')
 # Raw binding corruption must reject even control metadata; foreign output never returned.
 malformed=enqueue(env,ia,ra,key='corrupt-binding').json()
 from sim2act.lifecycle import run_instance
 from test_internal_lifecycle import limits
 foreign_sync=run_instance(store,B,ib['id'],1,rb['fingerprint'],{'column':'amount'},'foreign-sync',limits(envB))
 with store.tx() as c:
  original=dict(c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id==malformed['run_id'])).mappings().one())
  c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==malformed['run_id']).values(app_run_id=foreign_sync['id']))
 for url in [path(ia,malformed),path(ia,malformed)+'/control-status']:
  response=client.get(url);assert response.status_code==409,(url,response.text);assert '321.99' not in response.text and '4.00' not in response.text
 aggregate=client.get(f'/api/internal/instances/{ia["id"]}');assert aggregate.status_code==200;assert '321.99' not in aggregate.text;assert malformed['run_id'] not in {x['id'] for x in aggregate.json()['runs']}
 print('aggregate history omits corrupted foreign AppRun reference; does not expose foreign result')
 with store.tx() as c:
  c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==malformed['run_id']).values(app_run_id=original['app_run_id'],snapshot=[]))
 for suffix in ['', '/control-status']:
  response=client.get(path(ia,malformed)+suffix);assert response.status_code==409,response.text;assert '321.99' not in response.text
 with store.tx() as c:c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==malformed['run_id']).values(snapshot=original['snapshot']))
 print('malformed/foreign binding denies history+control without foreign output PASS')
 stopped=enqueue(env,ia2,ra,key='owner-stop-after-revoke').json()
 with store.tx() as c:
  runtime=c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id==aid)).scalar_one()
  c.execute(update(grants).where(grants.c.principal_id==runtime).values(revoked=True))
 for url in [path(ia2,stopped),f'/api/internal/instances/{ia2["id"]}',f'/api/internal/apps/{aid}/instances',f'/api/internal/releases/{ra["id"]}']:
  response=client.get(url);assert response.status_code==403,(url,response.text);assert '4.00' not in response.text and 'result' not in response.json().keys()
 response=client.get(path(ia2,stopped)+'/control-status');assert response.status_code==200,response.text
 control=response.json();assert control['content_access'] is False and not {'input','result','error','events','snapshot','data','known_effects'} & set(control)
 assert client.post(path(ia2,stopped)+'/commands',json={'command':'cancel','version':1}).json()['status']=='CANCELLED'
 client.headers.update({'Authorization':'Bearer synthetic-test-B'});assert client.get(path(ia2,stopped)+'/control-status').status_code==403
 print('app grant revoke denies protected history/results; owner stop metadata whitelist and cancellation PASS')
except Exception as e:
 print('review setup/result',type(e).__name__,str(e).split('\n')[0]);raise
finally:
 try:next(fixture)
 except StopIteration:pass
