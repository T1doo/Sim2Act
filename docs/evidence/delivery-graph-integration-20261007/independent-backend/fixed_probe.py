import sys,os,json,copy,hashlib
from pathlib import Path
ROOT=Path('/tmp/delivery-graph-adapter-independent/fixed-source-3f07');sys.path.insert(0,str(ROOT/'src'));sys.path.insert(1,str(ROOT/'tests'));os.chdir(ROOT)
import conftest
from test_conditional_run_bindings import env as bounded_env
from test_report_manifest_apps import promoted
from test_internal_lifecycle import setup_draft
from sqlalchemy import select,update
from sim2act.db import meta,fingerprint,app_drafts,grants,delivery_graph_anchors as anchors,delivery_graph_states as states,delivery_graph_requests as requests
from sim2act.delivery_graph_apps import set_lock,seal_outer
from sim2act.contracts import Limits
from sim2act.errors import DomainError
import sim2act.delivery_graph_apps as adapter
OUT=Path('/tmp/delivery-graph-adapter-independent');RESULTS=[]
def case(attack):
 tmp=OUT/('fixed-fixture-'+attack);tmp.mkdir(exist_ok=True);gen=conftest.env.__wrapped__(tmp);base=next(gen);env=bounded_env.__wrapped__(base)
 def snap():
  with env[0].tx() as c:return {t.name:sorted([dict(r) for r in c.execute(select(t)).mappings()],key=fingerprint) for t in meta.sorted_tables}
 def path(a):return f'/api/projects/{env[5]}/apps/{a}/delivery-graph'
 def derive(a,fp,key):
  r=env[2].post(path(a)+'/derive',json={'expected_candidate_fingerprint':fp,'request_key':key});assert r.status_code==201,r.text;return r.json()
 def request(graph,key):
  n=next(n for n in graph['graph']['nodes'] if n['kind']=='SOURCE');return {'expected_graph_fingerprint':graph['graph_fingerprint'],'request_key':key,'changes':[{'node_id':n['id'],'expected_revision':n['revision'],'expected_content_fingerprint':n['content_fingerprint']}]}
 try:
  app,_,_,_,wires=promoted(env,tmp);peer,pfp=setup_draft(base);pg=derive(peer,pfp,'peer');g=derive(app['id'],app['fingerprint'],'report');body=request(g,'original')
  baseline=snap();r=env[2].post(path(app['id'])+'/plans',json=body);assert r.status_code==201,r.text;original=r.json()
  assert original['receipt']['revalidation_scope']=='PROJECT';assert {app['id'],peer}=={v['app_id'] for v in original['expansion']['applications']}
  no_cache={k:v for k,v in original.items() if k!='cached'};assert no_cache['outer_fingerprint']==fingerprint({'core':no_cache['receipt'],'expansion':no_cache['expansion']});assert no_cache['native_outer_fingerprint']==fingerprint({k:v for k,v in no_cache.items() if k!='native_outer_fingerprint'})
  accepted=snap();assert all(baseline[t]==accepted[t] for t in baseline if not t.startswith('delivery_graph_'))
  if attack=='peer_anchor':
   with env[0].tx() as c:c.execute(update(anchors).where(anchors.c.app_id==peer).values(fingerprint='0'*64))
  elif attack=='peer_auth':
   with env[0].tx() as c:
    rt=c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id==peer)).scalar_one();gr=c.execute(select(grants).where(grants.c.principal_id==rt)).mappings().first();c.execute(update(grants).where(grants.c.id==gr['id']).values(expires_at=gr['expires_at']+1000))
  elif attack=='peer_graph_bool':
   with env[0].tx() as c:
    row=c.execute(select(states).where(states.c.app_id==peer)).mappings().one();v=copy.deepcopy(row['snapshot']);v['graph_revision']=True
    c.execute(update(states).where(states.c.app_id==peer).values(snapshot=v,fingerprint=fingerprint(v)));c.execute(update(anchors).where(anchors.c.id==row['anchor_id']).values(snapshot=v,fingerprint=fingerprint(v)))
  elif attack=='membership':setup_draft(base)
  elif attack in ['peer_lock','target_lock','wrong_lock_owner']:
   aid,graph,fp=(app['id'],g,app['fingerprint']) if attack=='target_lock' else (peer,pg,pfp)
   value={'expected_graph_fingerprint':graph['graph_fingerprint'],'request_key':'explicit-lock','change':request(graph,'ignored')['changes'][0],'locked':True}
   if attack=='wrong_lock_owner':
    before=snap()
    try:set_lock(env[0],env[4],env[5],aid,value,Limits(**{k:getattr(env[1],k) for k in Limits.model_fields}));raise AssertionError('wrong owner accepted')
    except DomainError as e:assert e.code=='PERMISSION_DENIED';assert snap()==before
    RESULTS.append({'case':attack,'decision':'PASS','code':e.code if False else 'PERMISSION_DENIED','all_tables_unchanged':True,'mock_count':len(wires)});return
   set_lock(env[0],env[3],env[5],aid,value,Limits(**{k:getattr(env[1],k) for k in Limits.model_fields}));locked=derive(aid,fp,'explicit-locked-anchor')
   if attack=='target_lock':g=locked;body=request(g,'original')
  elif attack=='coherent_outer_trim':
   with env[0].tx() as c:
    for row in c.execute(select(requests).where(requests.c.app_id==app['id'],requests.c.request_key=='original')).mappings():
     if row['kind'] not in ['plan','plan_seal']:continue
     data=copy.deepcopy(row['snapshot']);ans=data['response'];ans['scope_jobs']=[j for j in ans['scope_jobs'] if j['app_id']!=peer];ans['scope_expansion']['applications']=[j for j in ans['scope_expansion']['applications'] if j['app_id']!=peer];ans['scope_expansion']['membership']=[j for j in ans['scope_expansion']['membership'] if j['app_id']!=peer]
     ans['scope_expansion']['snapshot_fingerprint']=fingerprint(ans['scope_expansion']['applications']);ans['scope_expansion']['membership_fingerprint']=fingerprint(ans['scope_expansion']['membership']);ans.pop('expansion');ans.pop('outer_fingerprint');ans.pop('native_outer_fingerprint');seal_outer(ans);c.execute(update(requests).where(requests.c.id==row['id']).values(snapshot=data,fingerprint=fingerprint(data)))
  frozen=snap();retry=env[2].post(path(app['id'])+'/plans',json=body);hist=env[2].get(path(app['id'])+'/plans');assert retry.status_code>=400,(attack,retry.text);assert hist.status_code>=400,(attack,hist.text);assert snap()==frozen,attack
  fresh=env[2].post(path(app['id'])+'/plans',json=request(g,'new-after-invalid-peer'))
  if fresh.status_code<400:
   answer=fresh.json();assert answer['scope_expansion']['status']=='BLOCKED_PARTIAL';assert peer not in {j['app_id'] for j in answer['scope_jobs']} or attack in ['membership','coherent_outer_trim'];fresh_outcome='EXPLICIT_BLOCKED_PARTIAL'
  else:assert snap()==frozen;fresh_outcome='REJECTED_ZERO_WRITE'
  RESULTS.append({'case':attack,'decision':'PASS','replay_status':retry.status_code,'history_status':hist.status_code,'replay_history_all_tables_unchanged':True,'fresh_status':fresh.status_code,'fresh_outcome':fresh_outcome,'mock_count':len(wires),'whole_native_outer_seal_checked':True,'authority_unchanged_by_graph_operations':True})
 finally:
  try:next(gen)
  except StopIteration:pass
  for f in tmp.glob('fixture.db*'):f.unlink()
for attack in ['peer_anchor','peer_auth','peer_graph_bool','membership','peer_lock','target_lock','wrong_lock_owner','coherent_outer_trim']:
 case(attack);print(json.dumps(RESULTS[-1]),flush=True)
report={'source':'3f07b751a45cab522e754ab3f31b22034dafc26c','adapter_path':adapter.__file__,'adapter_sha256':hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),'decision':'LIMITED_ADAPTER_PASS','cases':RESULTS,'remaining':['raw SourceVersion bool/float core BLOCK separately; no full/PG/native/UI/concurrency','New invalid-peer requests explicitly create BLOCKED_PARTIAL ledger, not successful complete PROJECT jobs; cached/history reject with zero writes','No scheduler/patch/business/semantic acceptance; only private planning'],'cleanup':'All owned TestClient/Store closed; SQLite fixtures deleted'}
(OUT/'fixed-http-review.json').write_text(json.dumps(report,indent=2));print('FINAL',report['decision'])
