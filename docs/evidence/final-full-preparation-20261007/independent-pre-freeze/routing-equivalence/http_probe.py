import sys,os,json,copy,hashlib
from pathlib import Path
ROOT=Path('/tmp/csv-routing-hint-independent/source-4d');sys.path.insert(0,str(ROOT/'src'));sys.path.insert(1,str(ROOT/'tests'));os.chdir(ROOT)
import conftest
from test_conditional_run_bindings import env as bounded_env
from test_report_manifest_apps import promoted
from test_internal_lifecycle import setup_draft
from sqlalchemy import select,update,insert
from sim2act.db import meta,fingerprint,app_drafts,grants,runs,new_id
import sim2act.api as api
OUT=ROOT.parent;tmp=OUT/'http-fixture';tmp.mkdir(exist_ok=True);gen=conftest.env.__wrapped__(tmp);base=next(gen);env=bounded_env.__wrapped__(base);results=[]
def snapshot():
 with env[0].tx() as c:return {t.name:sorted([dict(r) for r in c.execute(select(t)).mappings()],key=fingerprint) for t in meta.sorted_tables}
def check_read(case,path,expected):
 before=snapshot();reply=env[2].get(path);after=snapshot();assert reply.status_code==expected,(case,reply.text);assert before==after;results.append({'case':case,'status':reply.status_code,'before_whole_database_fingerprint':fingerprint(before),'after_whole_database_fingerprint':fingerprint(after),'all_tables_unchanged':True});return reply
try:
 app,_,_,_,wires=promoted(env,tmp);csv,csvfp=setup_draft(base)
 with env[0].tx() as c:
  row=dict(c.execute(select(app_drafts).where(app_drafts.c.id==csv)).mappings().one());unknown=new_id('app');row.update(id=unknown,name='unknown shape',candidate={'namespace':'unknown.family.v1'},fingerprint=fingerprint({'namespace':'unknown.family.v1'}));c.execute(insert(app_drafts).values(**row))
 catalog=check_read('owner_catalog_advisory_only','/api/apps',200).json();items={x['id']:x for x in catalog['items']};assert items[app['id']]['csv_instance_candidate'] is False;assert items[csv]['csv_instance_candidate'] is True;assert 'csv_instance_candidate' not in items[unknown];assert all(set(x)<= {'id','name','project_id','csv_instance_candidate'} for x in items.values())
 check_read('true_csv_full_authoritative_inspect','/api/apps/'+csv,200);check_read('report_explicit_open_still_full_inspect','/api/apps/'+app['id'],200)
 def revoke_case(aid,rid,case):
  with env[0].tx() as c:
   conditions=(grants.c.principal_id==rid) if rid else (grants.c.resource_id==app['candidate']['report_proof']['source_resource_id'])
   old=[dict(r) for r in c.execute(select(grants).where(conditions)).mappings()]
   for g in old:c.execute(update(grants).where(grants.c.id==g['id']).values(revoked=True))
  check_read(case,'/api/apps/'+aid,403)
  # Catalog still only route metadata; a false hint is not proof of current authority.
  check_read(case+'_catalog_still_metadata','/api/apps',200)
  with env[0].tx() as c:
   for g in old:c.execute(update(grants).where(grants.c.id==g['id']).values(revoked=g['revoked']))
 with env[0].tx() as c:runtime=c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id==csv)).scalar_one()
 revoke_case(csv,runtime,'csv_runtime_revoke_denied');revoke_case(app['id'],None,'report_source_revoke_denied')
 sid=app['candidate']['report_proof']['source_run_id']
 with env[0].tx() as c:
  result=c.execute(select(runs.c.result).where(runs.c.id==sid)).scalar_one();c.execute(update(runs).where(runs.c.id==sid).values(result=None))
 check_read('report_source_null_denied_even_hintfalse','/api/apps/'+app['id'],409)
 with env[0].tx() as c:c.execute(update(runs).where(runs.c.id==sid).values(result=result))
 env[2].headers['Authorization']='Bearer synthetic-test-B';b=check_read('other_identity_catalog_owner_filter','/api/apps',200);assert b.json()['items']==[];check_read('other_identity_csv_denied','/api/apps/'+csv,403);check_read('other_identity_report_denied','/api/apps/'+app['id'],403)
 assert len(wires)==3
 r={'source':'4d1a486166436babffb76c2db96e87144ac9fb1a','decision':'LIMITED_HTTP_PASS','cases':results,'runtime_module_path':api.__file__,'runtime_module_sha256':hashlib.sha256(Path(api.__file__).read_bytes()).hexdigest(),'fixture_mock_calls':3,'product_read_provider_calls':0,'scope':'Actual TestClient ownSQLite; rawunknown row is test-only after baseline. No PG/full/LIVE/CI.'};(OUT/'http-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
finally:
 try:next(gen)
 except StopIteration:pass
 for f in tmp.glob('fixture.db*'):f.unlink()
