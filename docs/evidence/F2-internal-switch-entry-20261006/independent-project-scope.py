import sys,tempfile,pathlib,copy
sys.path.insert(0,'/workspace/Sim2Act-pb/tests')
import conftest
from test_internal_lifecycle import release,create,limits
from sim2act import lifecycle as L
from sim2act.db import internal_approvals,internal_instances,fingerprint
from sqlalchemy import select,update
fixture=conftest.env.__wrapped__(pathlib.Path(tempfile.mkdtemp(prefix='e22-review-')));env=next(fixture)
try:
 store,_,_,user,*_=env
 old,aid,fp=release(env);target,_,_=release(env,aid,fp);i=create(env,old);a=L.prepare_switch(store,user,i['id'],target['id'],1,limits(env))
 client=env[2];pid=client.post('/api/projects',json={'name':'synthetic other owner project'}).json()['id'];rid=client.post(f'/api/projects/{pid}/resources',json={'name':'other.csv','format':'csv','content':'amount\n2\n3\n'}).json()['id'];foreignenv=(*env[:5],pid,rid);old2,aid2,fp2=release(foreignenv);target2,_,_=release(foreignenv,aid2,fp2);i2=create(foreignenv,old2)
 with store.tx() as c:
  p=copy.deepcopy(c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id==a['id'])).scalar_one());p.update(instance_id=i2['id'],from_release_id=old2['id'],target_release_id=target2['id'],target_fingerprint=target2['fingerprint']);newfp=fingerprint(p);c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=p,fingerprint=newfp))
 response=client.post(f"/api/internal/instances/{i['id']}/switch-approvals/{a['id']}/commit",json={'fingerprint':newfp});print('HTTP wrong-project scope',response.status_code)
 try:
  result=L.commit_switch(store,user,a['id'],newfp,limits(env));print('direct commit wrong-project approval ACCEPTED',result['instance_id']==i2['id'],result['release_id']==target2['id'])
 except Exception as e:print('direct wrong-project commit rejected',type(e).__name__,str(e))
finally:
 try:next(fixture)
 except StopIteration:pass
