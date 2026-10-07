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
OUT=ROOT.parent;tmp=OUT/'actual-fixture';tmp.mkdir(exist_ok=True);gen=conftest.env.__wrapped__(tmp);base=next(gen);env=bounded_env.__wrapped__(base);results=[]
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
 for kind in ['source_null','extraction_null','check_anchor_deleted','source_current_bool','target_expired','source_format','coherent_target_bytes','wrong_parent_project','wrong_parent_id','typed_plan_mutation']:
  seen=[]
  def injected(store,c,user,pid,parentid):
   p,plan,job=original(store,c,user,pid,parentid);seen.append(parentid);p,plan=damage(c,p,plan,kind);return p,plan,job
  named._load_validated_origin=injected
  frozen=snap();reply=env[2].post(path,json=body);assert seen==[parent['id']],(kind,seen);assert reply.status_code in [400,403,409],(kind,reply.text);assert snap()==frozen,(kind,'writes')
  results.append({'case':'same_tx_'+kind,'status':reply.status_code,'code':reply.json()['error']['code'],'all_tables_unchanged_including_injection_rollback':True})
  named._load_validated_origin=original
 # Next HTTP request truly sees committed source null; cached operation cannot reuse prior validation.
 with env[0].tx() as c:
  old=dict(c.execute(select(runs).where(runs.c.id==sid)).mappings().one());c.execute(update(runs).where(runs.c.id==sid).values(result=None))
 frozen=snap();r=env[2].post(path,json=body);assert r.status_code==409,r.text;assert snap()==frozen
 results.append({'case':'next_request_cached_source_null','status':r.status_code,'all_tables_unchanged':True})
 with env[0].tx() as c:c.execute(update(runs).where(runs.c.id==sid).values(result=old['result']))
 # Two actual cold enqueue receipts with identical facts; each own Run must be checked.
 preview=f'/api/projects/{env[5]}/apps/{aid}/previews';ids=[]
 for key in ['cold-first','cold-second']:
  r=env[2].post(preview,json={'expected_candidate_fingerprint':app['fingerprint'],'input':facts(500),'request_key':key});assert r.status_code==202,r.text;ids.append(r.json()['run_id'])
 frozen=snap();h=env[2].get(f'/api/projects/{env[5]}/apps/{aid}/history');assert h.status_code==200,h.text;assert {x['run']['run_id'] for x in h.json()['history']}==set(ids);assert snap()==frozen;assert len(wires)==3
 results.append({'case':'independent_two_queued_cold_receipt_reads','status':200,'distinct_actual_runs':2,'provider_calls_after_fixture':0,'all_tables_unchanged':True})
 with env[0].tx() as c:
  row=c.execute(select(app_previews).where(app_previews.c.app_id==aid,app_previews.c.request_key=='cold-second')).mappings().one();c.execute(update(app_previews).where(app_previews.c.id==row['id']).values(output={**row['output'],'run_id':ids[0]}))
 frozen=snap();h=env[2].get(f'/api/projects/{env[5]}/apps/{aid}/history');assert h.status_code==409,h.text;assert snap()==frozen
 results.append({'case':'second_cold_replayed_first_run_identical_facts','status':409,'all_tables_unchanged':True})
 result={'source':'1258e5bfa5a423c251ab133fb0775ad7a1bba544','decision':'LIMITED_HTTP_PASS','cases':results,'loaded_modules':[{'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in [named,report]],'mock_calls':len(wires),'real_provider_calls':0,'scope':'OwnSQLite actual TestClient HTTP, fixture helpers only baseline; independent damage/oracles; no PG/full/native/CI/network/LIVE','remaining':['same-tx newpromotion path not separately repeated','Grant revision/revoke next request not yet actual','Owner verified callcount profile not used to claim90s timing improvement']}
 (OUT/'actual-http-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
 named._load_validated_origin=original if 'original' in globals() else named._load_validated_origin
 try:next(gen)
 except StopIteration:pass
 for f in tmp.glob('fixture.db*'):f.unlink()
