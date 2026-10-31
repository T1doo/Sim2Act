"""One frozen CLI/real-HTTP/Intern finite goal, clean stop and same-origin reopen."""
import datetime,hashlib,json,os,queue,sqlite3,subprocess,sys,threading,time
from pathlib import Path
import httpx

repo=Path('/workspace/Sim2Act');expected=sys.argv[1]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
root=Path('/workspace/scratch')/('exact-read-live-'+expected[:12]+'-20261031')
root.mkdir(exist_ok=False);workspace=root/'workspace'
report={'source_commit':expected,'classification':'REAL_CLI_REAL_LOOPBACK_HTTP_REAL_FIXED_INTERN_EXACT_SYNTHETIC_TEXT_NOT_COLD_PG_WINDOWS',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'max_real_requests':2,'max_repairs':0,'paid_cap':0,'fallback':'STOP',
        'input':'Keep the original source.\nPublish only the reviewed report.\n','starts':[],'real_requests':None,'status':'STARTED'}
(root/'runner.py').write_bytes(Path(__file__).read_bytes())
probe_code="import importlib,json,hashlib; from pathlib import Path; names=['api','worker','model','exact_read','synthetic_workspace','contracts','db']; print(json.dumps({n:{'path':str(Path(importlib.import_module('sim2act.'+n).__file__).resolve()),'sha256':hashlib.sha256(Path(importlib.import_module('sim2act.'+n).__file__).read_bytes()).hexdigest()} for n in names}))"
runtime=json.loads(subprocess.check_output([str(repo/'.venv/bin/python'),'-c',probe_code],cwd=repo,text=True))
for name,item in runtime.items():
 assert Path(item['path'])==repo/'src/sim2act'/(name+'.py')
 assert item['sha256']==hashlib.sha256(subprocess.check_output(['git','show',expected+':src/sim2act/'+name+'.py'],cwd=repo)).hexdigest()
report['runtime_modules']=runtime
def save():
 (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
def launch(new):
 cmd=[str(repo/'.venv/bin/python'),'-B','-u','-m','sim2act.cli','synthetic-workspace','--data-dir',str(workspace),'--control-stdin','--exact-read-live']+(['--new'] if new else [])
 p=subprocess.Popen(cmd,cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 q=queue.Queue(maxsize=128);lines=[];errors=[]
 def stdout():
  for line in p.stdout:
   lines.append(line)
   try:q.put_nowait(line)
   except queue.Full:raise RuntimeError('bounded stdout exceeded')
 def stderr():
  for line in p.stderr:errors.append(line)
 t=threading.Thread(target=stdout,daemon=True);t.start();e=threading.Thread(target=stderr,daemon=True);e.start()
 record={'command':cmd,'pid':p.pid,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};report['starts'].append(record);save()
 started=time.monotonic();ready=None
 while time.monotonic()-started<30:
  if p.poll() is not None:break
  try:line=q.get(timeout=.1)
  except queue.Empty:continue
  try:event=json.loads(line)
  except ValueError:continue
  if event.get('event')=='SYNTHETIC_WORKSPACE_READY':ready=event;break
 if not ready:
  # EOF is the original supported startup/shutdown path; no process kill/restart.
  p.stdin.close()
  try:p.wait(timeout=15)
  except subprocess.TimeoutExpired:record['owned_process_state']='UNKNOWN_AFTER_EOF'
  (root/('start-'+str(len(report['starts']))+'.stdout.jsonl')).write_text(''.join(lines))
  (root/('start-'+str(len(report['starts']))+'.stderr.log')).write_text(''.join(errors))
  raise RuntimeError('No real READY within original startup bound')
 record['ready']=ready;record['ready_seconds']=time.monotonic()-started;save()
 return p,t,e,lines,errors,record

def stop(state):
 p,t,e,lines,errors,record=state
 if record.get('owned_process_state','').startswith('UNKNOWN_'):return
 if p.poll() is None and not p.stdin.closed:
  p.stdin.write(json.dumps({'command':'stop','worker_id':record['ready']['worker_id']})+'\n');p.stdin.flush();p.stdin.close()
 try:code=p.wait(timeout=15)
 except subprocess.TimeoutExpired:
  record['owned_process_state']='UNKNOWN_AFTER_ORIGINAL_STOP';save();raise RuntimeError('Original STOP did not finish; no forced termination')
 t.join(timeout=2);e.join(timeout=2)
 events=[]
 for line in lines:
  try:events.append(json.loads(line))
  except ValueError:pass
 stopped=[x for x in events if x.get('event')=='SYNTHETIC_WORKSPACE_STOPPED']
 record.update(returncode=code,stopped=stopped,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 n=len([r for r in report['starts'] if 'returncode'in r])
 (root/f'start-{n}.stdout.jsonl').write_text(''.join(lines));(root/f'start-{n}.stderr.log').write_text(''.join(errors));save()
 assert code==0 and len(stopped)==1 and stopped[0]['worker_id']==record['ready']['worker_id']
 assert stopped[0]['clean'] and stopped[0]['worker_stopped'] and stopped[0]['data_preserved']

active=None
try:
 active=launch(True);origin=active[-1]['ready']['url'];report['origin']=origin
 with httpx.Client(base_url=origin,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=6) as c:
  page=c.get('/');assert page.status_code==200 and '已显式启用' in page.text and 'run-acceptance' in page.text
  project=c.post('/api/projects',json={'name':'Exact synthetic real model goal'});assert project.status_code==201
  pid=project.json()['id']
  resource=c.post(f'/api/projects/{pid}/resources',json={'name':'synthetic-exact.txt','format':'txt','content':report['input']});assert resource.status_code==201
  rid=resource.json()['id']
  body={'goal':'完整读取所选文本；最终仅返回JSON对象{"content":全部原文}，逐字核对并保存结果。',
        'resource_refs':[rid],'request_key':'exact-read:real-cli-once','acceptance':'exact-resource-read.v1'}
  accepted=c.post(f'/api/projects/{pid}/runs',json=body);assert accepted.status_code==202,accepted.status_code
  run_id=accepted.json()['run_id'];report.update(project=pid,resource=rid,run_id=run_id,request=body);save()
  states=[];started=time.monotonic();value=None
  while time.monotonic()-started<65:
   got=c.get('/api/runs/'+run_id);assert got.status_code==200,got.status_code
   value=got.json()
   if not states or states[-1]['status']!=value['status']:states.append({'status':value['status'],'seconds':time.monotonic()-started})
   if value['status'] not in {'QUEUED','RUNNING'}:break
   time.sleep(.1)
  report['states']=states;report['goal_seconds']=time.monotonic()-started;report['run_status']=value['status']
  (root/'saved-run.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');save()
  assert value['status']=='SUCCEEDED',json.dumps({'status':value['status'],'error':value.get('error')})
  result=value['result'];assert result['goal_acceptance']=='PASS_EXACT_READ_CONTRACT'
  assert result['task_acceptance']['whole_task_accepted'] is True and result['read_result']['content']==report['input']
  assert result['task_acceptance']['owner_acceptance']=='PENDING' and result['task_acceptance']['general_semantic_acceptance']=='NOT_RUN'
  assert len([x for x in value['events'] if x['kind']=='MODEL_RESERVED'])==2
  repeated=c.post(f'/api/projects/{pid}/runs',json=body);assert repeated.status_code==202 and repeated.json()['run_id']==run_id
  assert c.get('/api/runs/'+run_id).json()==value
  report['same_key_same_run_before_stop']=True
 stop(active);active=None
 # First new interpreter/service reopen before database archival or direct SQL probes.
 active=launch(False);assert active[-1]['ready']['url']==origin
 with httpx.Client(base_url=origin,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=6) as c:
  reopened=c.get('/api/runs/'+run_id);assert reopened.status_code==200 and reopened.json()==value
  repeated=c.post(f'/api/projects/{pid}/runs',json=body);assert repeated.status_code==202 and repeated.json()['run_id']==run_id
  assert c.get('/api/runs/'+run_id).json()==value
  report['first_new_process_same_origin_and_result']=True;report['same_key_same_run_after_restart']=True
 stop(active);active=None
 connection=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);connection.row_factory=sqlite3.Row
 aa=[dict(x) for x in connection.execute('SELECT * FROM attempts WHERE run_id=?',(run_id,))]
 rr=[dict(x) for x in connection.execute('SELECT * FROM reservations WHERE run_id=?',(run_id,))]
 oo=[dict(x) for x in connection.execute('SELECT * FROM operations WHERE run_id=?',(run_id,))];connection.close()
 assert len(aa)==len(rr)==2 and len(oo)==1 and all(a['status']=='RECEIVED' and a['mode']=='LIVE' for a in aa)
 usage=[json.loads(a['usage']) for a in aa];assert all(u['status']=='known' for u in usage)
 report.update(status='PASS',real_requests=2,attempt_states=[a['status'] for a in aa],
               usage=usage,total_tokens=sum(u['tokens']['total_tokens'] for u in usage),operation_states=[o['status'] for o in oo],
               no_replay_after_restart=True,result_version=value['version'])
 for a in aa:
  a['parameters']=json.loads(a['parameters']);a['usage']=json.loads(a['usage']);a['response']=json.loads(a['response'])
 (root/'received-attempts.json').write_text(json.dumps(aa,ensure_ascii=False,indent=2)+'\n')
except Exception as error:
 report['status']='STOPPED';report['error_type']=type(error).__name__
 report['error']=str(error)[:800] if type(error) in {AssertionError,RuntimeError} else 'details suppressed'
finally:
 if active is not None:
  try:stop(active)
  except Exception as error:report['cleanup_status']=type(error).__name__
 if report['status']!='PASS' and (workspace/'synthetic-workspace.db').is_file() and 'run_id' in report:
  try:
   con=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
   rows=[dict(x) for x in con.execute('SELECT status,response_model FROM attempts WHERE run_id=?',(report['run_id'],))];con.close()
   known=sum(r['response_model'] is not None for r in rows)
   report['reserved_attempts']=len(rows);report['received_http200_identities']=known
   report['send_outcome_without_received_identity']='UNKNOWN' if known<len(rows) else 'NONE'
   if known==len(rows):report['real_requests']=known
  except Exception:report['failure_accounting']='UNAVAILABLE_NO_RETRY'
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print(json.dumps({k:report.get(k) for k in ['source_commit','status','run_status','real_requests','total_tokens','goal_seconds','first_new_process_same_origin_and_result','no_replay_after_restart','error','cleanup_status']},ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if report['status']=='PASS' else 1)
