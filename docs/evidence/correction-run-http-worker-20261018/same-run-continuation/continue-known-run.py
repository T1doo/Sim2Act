import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/workspace/Sim2Act/src','/workspace/Sim2Act/tests']
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,fingerprint
from test_spec_app_operations import snapshot
root=Path('/workspace/Sim2Act');out=Path('/workspace/correction-run-http-continuation-20261018')
old=Path('/workspace/correction-run-http-worker-20261018');fixture=old/'pytest-temp/test_visible_rejection_correct0'
dbfile=fixture/'fixture.db';before_sha=hashlib.sha256(dbfile.read_bytes()).hexdigest()
assert before_sha=='ef4e53a96807567da12b7a00c8eecab68a21f8bebd61d1d5fc40191af52e5704'
info=json.loads((fixture/'info.json').read_text());rows=[json.loads(s) for s in (fixture/'http.ndjson').read_text().splitlines()]
receipts=[json.loads(r['response']['text']) for r in rows if '/correction-requests/' in r['request']['path'] and r['response']['status']==200]
receipt=receipts[-1];child=receipt['run_id'];iid=receipt['instance_id'];key=receipt['request_key']
info.update(recovery_key=key,expected_child=child,scenario='known-accepted-continuation',output=str(out/'page-result.json'))
(out/'info.json').write_text(json.dumps(info,indent=2)+'\n')
paths=sorted(p for p in (root/'src/sim2act').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.css','.html','.json'})
paths += [root/'tests/natural_spec_corrections_ui.cjs',root/'tests/test_natural_spec_corrections_ui.py']
def sources():return {str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
inputs=sources();(out/'input-before.json').write_text(json.dumps(inputs,indent=2)+'\n')
settings=Settings('sqlite:///'+str(dbfile),out,mode='mock',goal_planner_provider='intern-s2')
assert settings.token=='' and not settings.live_enabled
store=Store(settings.database_url,test_only=True);client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer synthetic-test-A'
before=snapshot(store);(out/'database-before.json').write_text(json.dumps(before,indent=2)+'\n')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();error=None;code=None;worker_requests=0
cmd=['node','tests/natural_spec_corrections_ui.cjs',str(out/'info.json')]
with (out/'node.stderr').open('w') as err,(out/'http.ndjson').open('w') as log:
 p=subprocess.Popen(cmd,cwd=root,env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True)
 try:
  for line in p.stdout:
   request=json.loads(line)
   if request.get('done'):break
   if request.get('command')=='worker':
    worker_requests+=1;raise AssertionError('Known-success continuation must never execute a Worker or resend a model')
   response=client.request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
   answer=dict(id=request['id'],status=response.status_code,text=response.text,content_type=response.headers.get('content-type'))
   if not request['path'].endswith(('.js','.css')) and request['path']!='/':log.write(json.dumps(dict(request=request,response=answer))+'\n');log.flush()
   p.stdin.write(json.dumps(answer)+'\n');p.stdin.flush()
  p.stdin.close();code=p.wait(timeout=20)
  assert code==0,(out/'node.stderr').read_text()
  page=json.loads((out/'page-result.json').read_text());assert page['status']=='PASS'
  assert len(page['run_views'])==1 and page['run_views'][0]['run']['id']==child and page['run_views'][0]['run']['status']=='SUCCEEDED'
  route=f'/api/internal/instances/{iid}/runs/{child}/spec-owner-review'
  s=client.get(route);assert s.status_code==200,s.text;s=s.json();assert s['owner_acceptance']=='ACCEPTED'
  after=snapshot(store)
  for table in ['runs','internal_app_runs','internal_instance_data','natural_owner_records','natural_owner_seals']:
   assert all(r in after[table] for r in before[table]),table
  assert before['internal_instance_data']==after['internal_instance_data']
  for before_body in [json.loads(r['response']['text']) for r in rows if r['request']['path']==f'/api/internal/instances/{iid}/runs/{info["run"]}' and r['response']['status']==200][:1]:
   parent_now=client.get(f'/api/internal/instances/{iid}/runs/{info["run"]}');assert parent_now.status_code==200,parent_now.text
   parent_now=parent_now.json()
   fields=['id','app_run_id','release_id','status','version','result','result_version','known_effects','events','steps','markdown_view']
   assert {k:before_body.get(k) for k in fields}=={k:parent_now.get(k) for k in fields}
   (out/'parent-history-comparison.json').write_text(json.dumps(dict(fields=fields,before=before_body,after=parent_now,equal=True),indent=2)+'\n')
  body=dict(request_key='no-recursive-correction',expected_owner_sequence=s['sequence'],declaration_id=s['latest']['id'],declaration_fingerprint=s['latest']['fingerprint'],expected_context_fingerprint=fingerprint(s['current']))
  reject=client.post(route.replace('/spec-owner-review','/correction-reviews'),json=body)
  assert reject.status_code==409 and 'Corrections-of-corrections' in reject.text,reject.text
  assert snapshot(store)==after
  (out/'history-proof.json').write_text(json.dumps(dict(parent_run_id=info['run'],child_run_id=child,old_rows_preserved=True,typed_rows_unchanged=True,recursive_status=reject.status_code,recursive_response=reject.json(),child_owner=s),indent=2)+'\n')
  (out/'database-after.json').write_text(json.dumps(after,indent=2)+'\n')
 except BaseException as e:
  error=repr(e)
 finally:
  if p.poll() is None:p.kill();p.wait(timeout=5)
  client.close();store.engine.dispose()
after_inputs=sources();(out/'input-after.json').write_text(json.dumps(after_inputs,indent=2)+'\n')
record=dict(status='PASS' if error is None else 'FAIL',error=error,argv=cmd,started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,node_returncode=code,source_drift=[k for k in inputs if inputs[k]!=after_inputs[k]],source_db_before_sha256=before_sha,source_db_after_sha256=hashlib.sha256(dbfile.read_bytes()).hexdigest(),first_fresh_pytest='FAIL_RETAINED',same_accepted_run=child,parent=info['run'],worker_requests=worker_requests,real_model_requests=0,classification='ACTUAL_TESTCLIENT_HTTP_JSDOM_SAME_SUCCESSFUL_RUN_COLD_OWNER_CONTINUATION_NO_WORKER_OR_MODEL')
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(error is not None)
