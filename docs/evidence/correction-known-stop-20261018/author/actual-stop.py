import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/workspace/Sim2Act/src','/workspace/Sim2Act/tests']
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,runs,internal_instance_data,attempts
from sim2act.worker import Worker
from test_natural_spec_apps import transport,SOURCE
from test_pb_natural_specs import drive_to_success
from test_natural_spec_owner_acceptance import preview,decision,state
from test_spec_app_operations import snapshot
root=Path('/workspace/Sim2Act');out=Path('/workspace/correction-known-stop-20261018')
source=Path('/workspace/correction-run-http-continuation-20261018/fixture-after-owner-continuation.db')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='fe1d87474e14b93a34a67ab592d3644bab74416f5d20da0d6558f5ee46bc5d7b'
fixture=out/'synthetic-stop.db';assert not fixture.exists();shutil.copyfile(source,fixture)
settings=Settings('sqlite:///'+str(fixture),out,mode='mock',goal_planner_provider='intern-s2');assert settings.token=='' and not settings.live_enabled
store=Store(settings.database_url,test_only=True);client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer synthetic-test-A'
old=json.loads(Path('/workspace/correction-run-http-continuation-20261018/info.json').read_text());iid=json.loads(Path('/workspace/correction-run-http-continuation-20261018/history-proof.json').read_text())['child_owner']['instance_id']
paths=sorted(p for p in (root/'src/sim2act').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.css','.html','.json'})+[root/'tests/natural_spec_corrections_ui.cjs',root/'tests/correction_run_entry.cjs']
def inputs():return {str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
before_inputs=inputs();(out/'input-before.json').write_text(json.dumps(before_inputs,indent=2)+'\n')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();error=None;code=None;revoke=[];child=None;model=[];claims=[]
try:
 i=client.get(f'/api/internal/instances/{iid}');assert i.status_code==200,i.text;i=i.json()
 accepted=client.post(f'/api/internal/instances/{iid}/runs',json=dict(expected_revision=i['revision'],expected_release_fingerprint=i['release_fingerprint'],input={},request_key='actual-stop-new-original-parent'))
 assert accepted.status_code==202,accepted.text;parent=accepted.json()['run_id']
 owner=json.loads(Path('/workspace/correction-run-http-worker-20261018/pytest-temp/test_visible_rejection_correct0/worker-proof.json').read_text())[0]['claims'][0]['before']['principal_id']
 data=(store,settings,client,owner,old['project'])
 claims=drive_to_success(data,parent,transport(model,SOURCE));(out/'parent-worker-proof.json').write_text(json.dumps(dict(run=parent,claims=claims,wire=model),indent=2)+'\n')
 route=f'/api/internal/instances/{iid}/runs/{parent}/spec-owner-review'
 p,_=preview(data,route,'explicit-stop-parent-owner');r=client.post(route+'-requests',json=decision(p,True));assert r.status_code==201,r.text
 parent_state=state(data,route);assert parent_state['owner_acceptance']=='REJECTED'
 before=snapshot(store);(out/'database-before-page.json').write_text(json.dumps(before,indent=2)+'\n')
 app=client.get('/api/apps/'+i['source_app_id']);assert app.status_code==200,app.text
 info=dict(project=old['project'],name=app.json()['name'],run=parent,goal_text=parent_state['current']['goal']['goal'],scenario='revoked-cancel',output=str(out/'page-result.json'))
 (out/'info.json').write_text(json.dumps(info,indent=2)+'\n')
 with (out/'node.stderr').open('w') as errors,(out/'http.ndjson').open('w') as log:
  proc=subprocess.Popen(['node','tests/natural_spec_corrections_ui.cjs',str(out/'info.json')],cwd=root,env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True)
  try:
   for line in proc.stdout:
    req=json.loads(line)
    if req.get('done'):break
    assert req.get('command')!='worker','Cancelled child must never be sent to a model'
    if req.get('command')=='revoke_known_material':
     assert not revoke
     child=req['rid'];meta=client.get(f'/api/internal/instances/{iid}/runs/{child}/control-status');assert meta.status_code==200 and meta.json()['status']=='QUEUED',meta.text
     source_id=parent_state['current']['material']['resource_id']
     grants=client.get(f'/api/projects/{old["project"]}/grants');assert grants.status_code==200
     found=[g for g in grants.json() if g['principal_id']==owner and g['resource_id']==source_id and g['tool_ref']=='resource.read' and not g['revoked']];assert len(found)==1
     g=found[0];revoked=client.post('/api/grants/'+g['id']+'/revoke',json=dict(command='revoke',version=g['revision']));assert revoked.status_code==200,revoked.text
     revoke.append(dict(grant=g,response=revoked.json(),child=child,resource=source_id));(out/'revocation.json').write_text(json.dumps(revoke,indent=2)+'\n')
     answer=dict(id=req['id'],status=200,text='{}')
    else:
     assert 'command' not in req
     response=client.request(req['method'],req['path'],json=req.get('body'),headers=req.get('headers'))
     answer=dict(id=req['id'],status=response.status_code,text=response.text,content_type=response.headers.get('content-type'))
     if not req['path'].endswith(('.js','.css')) and req['path']!='/':log.write(json.dumps(dict(request=req,response=answer))+'\n');log.flush()
    proc.stdin.write(json.dumps(answer)+'\n');proc.stdin.flush()
   proc.stdin.close();code=proc.wait(timeout=20);assert code==0,(out/'node.stderr').read_text()
  finally:
   if proc.poll() is None:proc.kill();proc.wait(timeout=5)
 page=json.loads((out/'page-result.json').read_text());assert page['status']=='PASS' and child
 calls=[]
 assert not Worker(store,settings,goal_planner_transport=transport(calls,SOURCE)).once();assert not calls
 with store.tx() as c:
  header=dict(c.execute(select(runs.c.id,runs.c.status,runs.c.cancel_intent).where(runs.c.id==child)).mappings().one())
  assert header['status']=='CANCELLED' and header['cancel_intent']
  assert not c.execute(select(attempts.c.id).where(attempts.c.run_id==child)).first()
  typed=[dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
  assert typed==before['internal_instance_data']
 after=snapshot(store);(out/'database-after-page.json').write_text(json.dumps(after,indent=2)+'\n')
 (out/'cancelled-child-proof.json').write_text(json.dumps(dict(header=header,child_attempts=0,post_cancel_worker_claimed=False,post_cancel_model_calls=0,typed_rows_unchanged=True,original_read_revoked=True,original_legacy_permissions_unchanged=True),indent=2)+'\n')
except BaseException as e:error=repr(e)
finally:client.close();store.engine.dispose()
after_inputs=inputs();(out/'input-after.json').write_text(json.dumps(after_inputs,indent=2)+'\n')
record=dict(status='PASS' if error is None else 'FAIL',error=error,started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,source_drift=[k for k in before_inputs if before_inputs[k]!=after_inputs[k]],fixture='EXACT_COPY_OF_CURRENT_TEST_SUCCESS_DB_THEN_NORMAL_NEW_PARENT_RUN',fixture_source_sha256='fe1d87474e14b93a34a67ab592d3644bab74416f5d20da0d6558f5ee46bc5d7b',parent_model_calls=len(model),child_model_calls=0,child=child,node_returncode=code,real_model_requests=0,classification='ACTUAL_TESTCLIENT_HTTP_JSDOM_REVOKED_SOURCE_EXPLICIT_CANCEL_NORMAL_PARENT_WORKER_MOCK1')
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(error is not None)
