import datetime,json,queue,signal,subprocess,threading,time
from pathlib import Path
import httpx
root=Path('/workspace/scratch/installed-default-cli-final-v2-20261031');root.mkdir(exist_ok=False)
workspace=root/'workspace';python='/workspace/scratch/limited-text-installed-format-v2-20261031/bin/python'
report={'classification':'INSTALLED_WHEEL_MANUAL_CLI_DEFAULT_NO_MODEL','candidate_source':'1a23c032fdc5ac83b4caf3ba07ed06f8a9d7669e','real_model_requests':0,'starts':[],'status':'STARTED'}
def save():(root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def start(new):
 cmd=[python,'-I','-B','-u','-m','sim2act.cli','synthetic-workspace','--data-dir',str(workspace)]+(['--new'] if new else [])
 p=subprocess.Popen(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 lines=[];errors=[];q=queue.Queue(maxsize=128)
 def consume(stream,target,enqueue=False):
  for line in stream:
   target.append(line)
   if enqueue:q.put_nowait(line)
 t=threading.Thread(target=consume,args=(p.stdout,lines,True),daemon=True);e=threading.Thread(target=consume,args=(p.stderr,errors),daemon=True);t.start();e.start()
 record={'command':cmd,'pid':p.pid};report['starts'].append(record);save();until=time.monotonic()+25
 while time.monotonic()<until:
  if p.poll() is not None:break
  try:line=q.get(timeout=.1)
  except queue.Empty:continue
  try:ready=json.loads(line)
  except ValueError:continue
  if ready.get('event')=='SYNTHETIC_WORKSPACE_READY':record['ready']=ready;return p,t,e,lines,errors,record
 raise RuntimeError('No normal READY; do not restart unknown process')
def stop(s):
 p,t,e,lines,errors,r=s
 if p.poll() is None:p.send_signal(signal.SIGINT)
 code=p.wait(timeout=15);t.join(2);e.join(2)
 assert not t.is_alive() and not e.is_alive()
 items=[]
 for line in lines:
  try:items.append(json.loads(line))
  except ValueError:pass
 stopped=[x for x in items if x.get('event')=='SYNTHETIC_WORKSPACE_STOPPED']
 r.update(returncode=code,stopped=stopped,stdout_eof=True,stderr_eof=True)
 n=len(report['starts']);(root/f'start-{n}.stdout.jsonl').write_text(''.join(lines));(root/f'start-{n}.stderr.log').write_text(''.join(errors));save()
 assert code==0 and len(stopped)==1 and stopped[0]['clean'] and stopped[0]['data_preserved']
active=None
try:
 active=start(True);url=active[-1]['ready']['url'];assert active[-1]['ready']['control_stdin'] is False
 with httpx.Client(base_url=url,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=5) as c:
  page=c.get('/');assert page.status_code==200 and 'run-acceptance' in page.text and '已显式启用' not in page.text
  project=c.post('/api/projects',json={'name':'Installed default synthetic project'});assert project.status_code==201
  pid=project.json()['id'];resource=c.post(f'/api/projects/{pid}/resources',json={'name':'default.txt','format':'txt','content':'Retain the default input.\n'});assert resource.status_code==201
  body={'goal':'Arbitrary free goal is explicitly unsupported here','resource_refs':[resource.json()['id']],'request_key':'installed-default-no-model'}
  submitted=c.post(f'/api/projects/{pid}/runs',json=body);assert submitted.status_code==202
  rid=submitted.json()['run_id'];until=time.monotonic()+15
  while time.monotonic()<until:
   got=c.get('/api/runs/'+rid);assert got.status_code==200;value=got.json()
   if value['status'] not in {'QUEUED','RUNNING'}:break
   time.sleep(.1)
  assert value['status']=='FAILED' and value['error']['code']=='UNSUPPORTED_CAPABILITY',value.get('error')
  assert c.post(f'/api/projects/{pid}/runs',json=body).json()['run_id']==rid
  (root/'saved-run.json').write_text(json.dumps(value,indent=2)+'\n')
 stop(active);active=None
 active=start(False);url2=active[-1]['ready']['url']
 with httpx.Client(base_url=url2,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=5) as c:
  assert c.get('/api/runs/'+rid).json()==value
  assert c.post(f'/api/projects/{pid}/runs',json=body).json()['run_id']==rid
  assert c.get('/api/runs/'+rid).json()==value
 stop(active);active=None
 report.update(status='PASS',run_id=rid,free_goal_result='FAILED/UNSUPPORTED_CAPABILITY',same_key_same_run=True,first_reopen_same_result=True,first_origin=url,second_origin=url2,origin_guarantee='Plain CLI random port; use each READY URL, not desktop owned-stdin stable-origin claim')
finally:
 if active is not None:stop(active)
 save();print(json.dumps(report,indent=2))
