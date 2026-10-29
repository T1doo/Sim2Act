import hashlib,json,os,queue,subprocess,sys,threading,time
from pathlib import Path
import httpx
repo=Path('/workspace/Sim2Act'); root=Path('/workspace/scratch/blank-desktop-flow-20261029-r2');root.mkdir(exist_ok=False)
log=(root/'backend.log').open('w');pending=queue.Queue();rows=[];calls=[]
def start(new):
 global pending
 pending=queue.Queue()
 command=[str(repo/'.venv/bin/python'),'-B','-u','-m','sim2act.cli','synthetic-workspace','--data-dir',str(root/'data'),'--control-stdin']+(['--new'] if new else [])
 child=subprocess.Popen(command,cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 def read():
  for line in child.stdout:
   log.write(line);log.flush()
   try:event=json.loads(line)
   except ValueError:continue
   rows.append(event);pending.put(event)
  pending.put(None)
 thread=threading.Thread(target=read,daemon=True);thread.start();end=time.monotonic()+20
 while time.monotonic()<end:
  event=pending.get(timeout=max(.01,end-time.monotonic()))
  assert event is not None,'Backend exited before READY'
  if event.get('event')=='SYNTHETIC_WORKSPACE_READY':return child,thread,event
 raise AssertionError('No real READY')
def stop(child,thread,ready):
 child.stdin.write(json.dumps(dict(command='stop',worker_id=ready['worker_id']))+'\n');child.stdin.flush();child.stdin.close()
 code=child.wait(timeout=25);thread.join(2);assert not thread.is_alive() and code==0
 stopped=[r for r in rows if r.get('event')=='SYNTHETIC_WORKSPACE_STOPPED' and r.get('worker_id')==ready['worker_id']]
 assert len(stopped)==1 and all(stopped[0].get(k) is True for k in ('clean','worker_stopped','data_preserved'))
def client(ready):return httpx.Client(base_url=ready['url'],headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=10)
def request(c,method,path,body=None,status=200):
 response=c.request(method,path,json=body) if body is not None else c.request(method,path)
 calls.append(dict(method=method,path=path,status=response.status_code));assert response.status_code==status,(path,response.status_code,response.text)
 return response.json()
child,thread,ready=start(True)
try:
 with client(ready) as c:
  project=request(c,'POST','/api/projects',dict(name='Blank desktop synthetic CSV'),201)['id']
  resource=request(c,'POST',f'/api/projects/{project}/resources',dict(name='practice.csv',format='csv',content='item,amount,quantity\nA,10,7\nB,20,8\n'),201)
  app=request(c,'POST',f'/api/projects/{project}/apps/csv-preview',dict(name='Desktop CSV sum',resource_id=resource['id'],goal='Sum explicitly selected column'),201)
  app=request(c,'GET','/api/apps/'+app['id'])
  approval=request(c,'POST',f"/api/internal/apps/{app['id']}/release-approvals",dict(expected_draft_fingerprint=app['fingerprint'],sample_input=dict(column='amount')),201)
  release=request(c,'POST',f"/api/internal/approvals/{approval['id']}/commit",dict(fingerprint=approval['fingerprint']))
  instance=request(c,'POST',f"/api/internal/releases/{release['id']}/instances",dict(expected_release_fingerprint=release['fingerprint'],request_key='desktop-instance'),201)
  results=[]
  for version,(column,total) in enumerate((('amount','30'),('quantity','15')),1):
   queued=request(c,'POST',f"/api/internal/instances/{instance['id']}/runs",dict(expected_release_fingerprint=release['fingerprint'],expected_revision=instance['revision'],input=dict(column=column),request_key='desktop-'+column),202)
   end=time.monotonic()+30
   while True:
    run=request(c,'GET','/api/runs/'+queued['run_id'])
    if run['status'] not in ('QUEUED','RUNNING'):break
    assert time.monotonic()<end,'Original CSV run did not finish';time.sleep(.15)
   assert run['status']=='SUCCEEDED',run
   path=f"/api/internal/instances/{instance['id']}/runs/{queued['run_id']}"
   detail=request(c,'GET',path);assert detail['result_version']==version and detail['result']['sum']==total
   results.append(dict(path=path,detail=detail))
finally:stop(child,thread,ready)
child,thread,ready=start(False)
try:
 with client(ready) as c:
  for saved in results:assert request(c,'GET',saved['path'])==saved['detail'],'Cold reopen changed the saved result'
finally:stop(child,thread,ready)
report=dict(classification='REAL_PRODUCT_CLI_HTTP_SQLITE_WORKER_CONTROL_PIPE_NOT_NATIVE_WINDOW_NOT_INSTALLED_WHEEL_NOT_PG_NOT_MODEL',status='PASS',source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),source_worktree=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True),results=[dict(version=r['detail']['result_version'],sum=r['detail']['result']['sum'],path=r['path']) for r in results],model_calls=0,mock_model_calls=0,ready_count=sum(r.get('event')=='SYNTHETIC_WORKSPACE_READY' for r in rows),clean_stop_count=sum(r.get('event')=='SYNTHETIC_WORKSPACE_STOPPED' and r.get('clean') is True for r in rows),http_calls=calls,data_preserved=True,cold_read_equal=True)
(root/'result.json').write_text(json.dumps(report,indent=2)+'\n');log.close();print(json.dumps({k:v for k,v in report.items() if k not in ('http_calls','source_worktree')},indent=2))
