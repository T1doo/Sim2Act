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
 old,aid,fp=release(env);target,_,_=release(env,aid,fp);foreign,_,_=release(env);i=create(env,old);a=L.prepare_switch(store,user,i['id'],target['id'],1,limits(env))
 with store.tx() as c:
  p=copy.deepcopy(c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id==a['id'])).scalar_one());p['target_release_id']=foreign['id'];p['target_fingerprint']=foreign['fingerprint'];newfp=fingerprint(p);c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=p,fingerprint=newfp))
 try:
  result=L.commit_switch(store,user,a['id'],newfp,limits(env));print('coherent foreign-app approval commit ACCEPTED',result['release_id']==foreign['id'])
 except Exception as e:print('coherent foreign-app approval rejected',type(e).__name__,str(e))
 # Distinct untouched instance for malformed payload.
 i2=create(env,old);b=L.prepare_switch(store,user,i2['id'],target['id'],1,limits(env))
 with store.tx() as c:
  p=copy.deepcopy(c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id==b['id'])).scalar_one());p.pop('instance_id');newfp=fingerprint(p);c.execute(update(internal_approvals).where(internal_approvals.c.id==b['id']).values(payload=p,fingerprint=newfp))
 try:L.commit_switch(store,user,b['id'],newfp,limits(env));print('malformed payload accepted')
 except Exception as e:print('malformed payload rejection',type(e).__name__,str(e))
finally:
 try:next(fixture)
 except StopIteration:pass
