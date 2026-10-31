"""One frozen CLI/real-HTTP/Intern finite goal, clean stop and same-origin reopen."""
import datetime,hashlib,json,os,queue,sqlite3,subprocess,sys,threading,time
from pathlib import Path
import httpx

repo=Path('/workspace/Sim2Act');expected=sys.argv[1]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
root=Path('/workspace/scratch')/('exact-read-live-'+expected[:12]+'-20261031')
root.mkdir(exist_ok=False);installed_python='/workspace/scratch/limited-text-installed-format-v2-20261031/bin/python'
installed_package=Path('/workspace/scratch/limited-text-installed-format-v2-20261031/lib/python3.12/site-packages/sim2act')
workspace=Path('/workspace/scratch/exact-read-live-9d74a3a17520-20261031/workspace')
old_root=workspace.parent
old_report=json.loads((old_root/'report.json').read_text())
old_value=json.loads((old_root/'saved-run.json').read_text())
def old_rows():
 con=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 value={t:[dict(r) for r in con.execute('SELECT * FROM '+t+' WHERE '+('id' if t=='runs' else 'run_id')+'=? ORDER BY 1',(old_value['id'],))] for t in ['runs','attempts','reservations','events','run_contracts']}
 con.close();return value
original_rows=old_rows()
assert len(original_rows['attempts'])==1 and original_rows['attempts'][0]['status']=='FAILED'
assert json.loads(original_rows['attempts'][0]['usage'])['status']=='unknown'
prior_success=json.loads(Path('/workspace/scratch/exact-read-live-fc978d312bc2-20261031/report.json').read_text())
prior_success_value=json.loads(Path('/workspace/scratch/exact-read-live-fc978d312bc2-20261031/saved-run.json').read_text())
def success_rows():
 con=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 value={t:[dict(r) for r in con.execute('SELECT * FROM '+t+' WHERE '+('id' if t=='runs' else 'run_id')+' IN (?,?) ORDER BY 1',(prior_success['run_id'],prior_previous['run_id']))] for t in ['runs','attempts','reservations','events','run_contracts']}
 con.close();return value
prior_previous=json.loads(Path('/workspace/scratch/exact-read-live-6424cc040bc8-20261031/report.json').read_text())
prior_previous_value=json.loads(Path('/workspace/scratch/exact-read-live-6424cc040bc8-20261031/saved-run.json').read_text())
original_success_rows=success_rows();assert len(original_success_rows['attempts'])==4
format_report=json.loads(Path('/workspace/scratch/failed-installed-original-2175eae7-20261031/report.json').read_text())
format_value=json.loads(Path('/workspace/scratch/failed-installed-original-2175eae7-20261031/saved-run.json').read_text())
def format_rows():
 con=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 result={t:[dict(r) for r in con.execute('SELECT * FROM '+t+' WHERE '+('id' if t=='runs' else 'run_id')+'=? ORDER BY 1',(format_report['run_id'],))] for t in ['runs','attempts','reservations','events','run_contracts']};con.close();return result
original_format_rows=format_rows();assert len(original_format_rows['attempts'])==2
original_rows_hash=hashlib.sha256(json.dumps(original_rows,sort_keys=True).encode()).hexdigest()
report={'source_commit':expected,'classification':'REAL_INSTALLED_WHEEL_CLI_REAL_LOOPBACK_HTTP_REAL_FIXED_INTERN_EXACT_SYNTHETIC_TEXT_NOT_COLD_PG_WINDOWS',
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'max_new_requests':2,'max_total_reserved_requests_including_prior_unknown':9,'prior_received_requests':6,'prior_success_goal_requests':4,'prior_format_failed_goal_requests':2,'prior_failed_source':old_report['source_commit'],'prior_failed_run':old_value['id'],'prior_unknown_requests':1,'prior_rows_sha256':original_rows_hash,'max_repairs':0,'paid_cap':0,'fallback':'STOP',
        'input':'Read the final installed text.\nKeep its final newline.\n','starts':[],'real_requests':None,'status':'STARTED'}
(root/'runner.py').write_bytes(Path(__file__).read_bytes())
probe_code="import importlib,json,hashlib; from pathlib import Path; names=['api','worker','model','exact_read','synthetic_workspace','contracts','db','natural_spec_runtime','model_settlement']; print(json.dumps({n:{'path':str(Path(importlib.import_module('sim2act.'+n).__file__).resolve()),'sha256':hashlib.sha256(Path(importlib.import_module('sim2act.'+n).__file__).read_bytes()).hexdigest()} for n in names}))"
runtime=json.loads(subprocess.check_output([installed_python,'-I','-B','-c',probe_code],cwd=root,text=True))
for name,item in runtime.items():
 assert Path(item['path'])==installed_package/(name+'.py')
 assert item['sha256']==hashlib.sha256(subprocess.check_output(['git','show',expected+':src/sim2act/'+name+'.py'],cwd=repo)).hexdigest()
report['runtime_modules']=runtime
report['installed_wheel_sha256']='7133424e80ae46513c046c393db30a66f4c1f85d5443192fbfb8e8dd4ba7fed2'
report['candidate_zip_sha256']='b63d954d892023adafbdf062130ca23c5261cae38f6c108972c18988246f194e'
report['dependencies']='Reused existing pinned runtime dependencies via explicit test-only .pth; not a clean dependency download test'
report['isolation']='New venv application installed from wheel; -I; service cwd outside source; module byte hashes match frozen Git blobs'
def save():
 (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
def launch(new):
 cmd=[installed_python,'-I','-B','-u','-m','sim2act.cli','synthetic-workspace','--data-dir',str(workspace),'--control-stdin','--exact-read-live']+(['--new'] if new else [])
 p=subprocess.Popen(cmd,cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
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
 assert not t.is_alive() and not e.is_alive(), "Both owned output streams must reach EOF"
 record["stdout_eof"]=True;record["stderr_eof"]=True
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
 active=launch(False);origin=active[-1]['ready']['url'];report['origin']=origin
 with httpx.Client(base_url=origin,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=6) as c:
  old_got=c.get('/api/runs/'+old_value['id']);assert old_got.status_code==200 and old_got.json()==old_value
  old_duplicate=c.post('/api/projects/'+old_report['project']+'/runs',json=old_report['request']);assert old_duplicate.status_code==202 and old_duplicate.json()['run_id']==old_value['id']
  assert old_rows()==original_rows and success_rows()==original_success_rows and format_rows()==original_format_rows
  page=c.get('/');assert page.status_code==200 and '已显式启用' in page.text and 'run-acceptance' in page.text
  project=c.post('/api/projects',json={'name':'Explicit finite direct text goal'});assert project.status_code==201
  pid=project.json()['id']
  resource=c.post(f'/api/projects/{pid}/resources',json={'name':'synthetic-exact.txt','format':'txt','content':report['input']});assert resource.status_code==201
  rid=resource.json()['id']
  body={'goal':'完整读取所选文本；最终仅返回JSON对象{"content":全部原文}，逐字核对并保存结果。',
        'resource_refs':[rid],'request_key':'exact-read:json-only-v2-installed-once','acceptance':'exact-resource-read.v1'}
  accepted=c.post(f'/api/projects/{pid}/runs',json=body);assert accepted.status_code==202,accepted.status_code
  run_id=accepted.json()['run_id'];report.update(project=pid,resource=rid,run_id=run_id,request=body);save()
  states=[];started=time.monotonic();value=None
  while time.monotonic()-started<85:
   got=c.get('/api/runs/'+run_id);assert got.status_code==200,got.status_code
   value=got.json()
   if not states or states[-1]['status']!=value['status']:states.append({'status':value['status'],'seconds':time.monotonic()-started})
   if value['status'] not in {'QUEUED','RUNNING'}:break
   time.sleep(.1)
  report['states']=states;report['goal_seconds']=time.monotonic()-started;report['run_status']=value['status']
  (root/'saved-run.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');save()
  assert old_rows()==original_rows and success_rows()==original_success_rows and format_rows()==original_format_rows
  assert value['contract']['snapshot']['exact_read']['request_protocol']=='exact-read-direct.v2'
  assert value['status']=='SUCCEEDED',json.dumps({'status':value['status'],'error':value.get('error')})
  result=value['result'];assert result['goal_acceptance']=='PASS_EXACT_READ_CONTRACT'
  assert result['task_acceptance']['whole_task_accepted'] is True and result['read_result']['content']==report['input']
  assert result['task_acceptance']['owner_acceptance']=='PENDING' and result['task_acceptance']['general_semantic_acceptance']=='NOT_RUN'
  assert len([x for x in value['events'] if x['kind']=='MODEL_RESERVED'])==2
  repeated=c.post(f'/api/projects/{pid}/runs',json=body);assert repeated.status_code==202 and repeated.json()['run_id']==run_id
  assert c.get('/api/runs/'+run_id).json()==value
  report['same_key_same_run_before_stop']=True
 stop(active);active=None
 # First new service reopen before any SQL read of the new Run result; earlier SQL only checked preservation of prior failed and successful Runs.
 active=launch(False);assert active[-1]['ready']['url']==origin
 with httpx.Client(base_url=origin,headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=6) as c:
  reopened=c.get('/api/runs/'+run_id);assert reopened.status_code==200 and reopened.json()==value
  repeated=c.post(f'/api/projects/{pid}/runs',json=body);assert repeated.status_code==202 and repeated.json()['run_id']==run_id
  assert c.get('/api/runs/'+run_id).json()==value
  report['first_new_process_same_origin_and_result']=True;report['same_key_same_run_after_restart']=True
  assert c.get('/api/runs/'+old_value['id']).json()==old_value
  assert c.get('/api/runs/'+prior_success['run_id']).json()==prior_success_value
  assert c.get('/api/runs/'+prior_previous['run_id']).json()==prior_previous_value
  assert c.get('/api/runs/'+format_report['run_id']).json()==format_value
  assert old_rows()==original_rows and success_rows()==original_success_rows and format_rows()==original_format_rows
 stop(active);active=None
 connection=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True);connection.row_factory=sqlite3.Row
 aa=[dict(x) for x in connection.execute('SELECT * FROM attempts WHERE run_id=?',(run_id,))]
 rr=[dict(x) for x in connection.execute('SELECT * FROM reservations WHERE run_id=?',(run_id,))]
 oo=[dict(x) for x in connection.execute('SELECT * FROM operations WHERE run_id=?',(run_id,))];connection.close()
 assert len(aa)==len(rr)==2 and len(oo)==1 and all(a['status']=='RECEIVED' and a['mode']=='LIVE' for a in aa)
 assert old_rows()==original_rows and success_rows()==original_success_rows and format_rows()==original_format_rows
 usage=[json.loads(a['usage']) for a in aa];assert all(u['status']=='known' for u in usage)
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected
 final_porcelain=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip();assert not final_porcelain
 report.update(final_source_commit=expected,final_porcelain=final_porcelain,status='PASS',real_requests=2,attempt_states=[a['status'] for a in aa],
               usage=usage,total_tokens=sum(u['tokens']['total_tokens'] for u in usage),operation_states=[o['status'] for o in oo],
               no_replay_after_restart=True,run_control_version=value['version'],prior_unknown_history_unchanged=True)
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
 report['prior_unknown_history_unchanged']=old_rows()==original_rows
 report['prior_success_history_unchanged']=success_rows()==original_success_rows
 report['prior_format_failure_history_unchanged']=format_rows()==original_format_rows
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print(json.dumps({k:report.get(k) for k in ['source_commit','status','run_status','real_requests','total_tokens','goal_seconds','first_new_process_same_origin_and_result','no_replay_after_restart','error','cleanup_status']},ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if report['status']=='PASS' else 1)
