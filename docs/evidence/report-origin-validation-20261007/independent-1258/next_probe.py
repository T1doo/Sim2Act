import sys,os,json,copy,hashlib
from pathlib import Path
ROOT=Path('/tmp/validated-origin-bundle-independent/source-1258');sys.path.insert(0,str(ROOT/'src'));sys.path.insert(1,str(ROOT/'tests'));os.chdir(ROOT)
import conftest
from test_conditional_run_bindings import env as bounded_env,facts
from test_report_manifest_apps import promoted
from sqlalchemy import select,update,delete
from sim2act import conditional_apps as named,report_manifest_apps as report
from sim2act.db import meta,fingerprint,runs,protocol_jobs,events,resources,grants,app_previews
from sim2act.conditional_runs import CHECK_EVENT,ANCHOR_EVENT
OUT=ROOT.parent;tmp=OUT/'next-fixture';tmp.mkdir(exist_ok=True);gen=conftest.env.__wrapped__(tmp);base=next(gen);env=bounded_env.__wrapped__(base);results=[]
def snap():
 with env[0].tx() as c:return {t.name:sorted([dict(r) for r in c.execute(select(t)).mappings()],key=fingerprint) for t in meta.sorted_tables}
try:
 app,parent,path,body,wires=promoted(env,tmp);aid=app['id'];sid=app['candidate']['report_proof']['source_run_id'];eid=parent['origin']['extraction_run_id'];tid=parent['origin']['target_resource_id'];srcid=app['candidate']['report_proof']['source_resource_id'];original=named._load_validated_origin
 assert len(wires)==3;frozen=snap();cached=env[2].post(path,json=body);opened=env[2].get(f'/api/projects/{env[5]}/apps/{aid}');assert cached.status_code==201 and cached.json()['cached'];assert opened.status_code==200;assert opened.json()['candidate']==app['candidate'];assert snap()==frozen
 results.append({'case':'public_compatible_cached_and_read','status':[201,200],'candidate_unchanged':True,'all_tables_unchanged':True})
 def damage(c,p,plan,kind):
  if kind=='source_null':c.execute(update(runs).where(runs.c.id==sid).values(result=None))
  elif kind=='extraction_null':c.execute(update(runs).where(runs.c.id==eid).values(result=None))
  elif kind=='check_anchor_deleted':
   rec=c.execute(select(events.c.data).where(events.c.run_id==sid,events.c.kind==CHECK_EVENT)).scalar_one();c.execute(delete(events).where(events.c.run_id==rec['check_id'],events.c.kind==ANCHOR_EVENT))
  elif kind=='source_current_bool':c.execute(update(runs).where(runs.c.id==sid).values(version=True))
  elif kind=='target_expired':c.execute(update(grants).where(grants.c.project_id==env[5],grants.c.resource_id==tid).values(expires_at=0))
  elif kind=='source_format':c.execute(update(resources).where(resources.c.id==srcid).values(format='csv'))
  elif kind=='coherent_target_bytes':c.execute(update(resources).where(resources.c.id==tid).values(content='new finite contents',hash=hashlib.sha256(b'new finite contents').hexdigest()))
  elif kind=='wrong_parent_project':p={**p,'project_id':'proj_'+'0'*32}
  elif kind=='wrong_parent_id':p={**p,'id':'app_'+'0'*32}
  elif kind=='typed_plan_mutation':plan=copy.deepcopy(plan);plan['compiler_version']=True
  return p,plan

 for kind in ['source_grant_revoke','source_bytes_coherent','source_check_bool_rehash','target_grant_expiry','wrong_http_identity']:
  restore=[]
  with env[0].tx() as c:
   if kind in ['source_grant_revoke','target_grant_expiry']:
    rid=srcid if kind=='source_grant_revoke' else tid
    records=[dict(x) for x in c.execute(select(grants).where(grants.c.project_id==env[5],grants.c.resource_id==rid)).mappings()]
    for row in records:
     field='revoked' if kind=='source_grant_revoke' else 'expires_at';restore.append((grants,row['id'],{field:row[field]}));c.execute(update(grants).where(grants.c.id==row['id']).values(**{field:True if field=='revoked' else 0}))
   elif kind=='source_bytes_coherent':
    row=dict(c.execute(select(resources).where(resources.c.id==srcid)).mappings().one());restore.append((resources,srcid,{'content':row['content'],'hash':row['hash']}));c.execute(update(resources).where(resources.c.id==srcid).values(content='changed current source bytes',hash=hashlib.sha256(b'changed current source bytes').hexdigest()))
   elif kind=='source_check_bool_rehash':
    row=dict(c.execute(select(events).where(events.c.run_id==sid,events.c.kind==CHECK_EVENT)).mappings().one());d=copy.deepcopy(row['data']);d['value']['version']=True;d['fingerprint']=fingerprint(d['value']);restore.append((events,row['id'],{'data':row['data']}));c.execute(update(events).where(events.c.id==row['id']).values(data=d))
  if kind=='wrong_http_identity':env[2].headers['Authorization']='Bearer synthetic-test-B'
  frozen=snap();reply=env[2].post(path,json=body);after=snap();assert reply.status_code in [400,403,409],(kind,reply.text);assert after==frozen
  results.append({'case':'next_cached_'+kind,'status':reply.status_code,'code':reply.json()['error']['code'],'before_whole_database_fingerprint':fingerprint(frozen),'after_whole_database_fingerprint':fingerprint(after),'before_table_fingerprints':{k:fingerprint(v) for k,v in frozen.items()},'after_table_fingerprints':{k:fingerprint(v) for k,v in after.items()},'all_tables_unchanged':True,'previous_accepted_receipt_rows_unchanged':True})
  env[2].headers['Authorization']='Bearer synthetic-test-A'
  with env[0].tx() as c:
   for table,key,values in restore:c.execute(update(table).where(table.c.id==key).values(**values))
 result={'source':'1258e5bfa5a423c251ab133fb0775ad7a1bba544','decision':'LIMITED_NEXT_REQUEST_HTTP_PASS','cases':results,'mock_calls':len(wires),'provider_calls_after_fixture':0}
 (OUT/'next-http-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
 try:next(gen)
 except StopIteration:pass
 for f in tmp.glob('fixture.db*'):f.unlink()
