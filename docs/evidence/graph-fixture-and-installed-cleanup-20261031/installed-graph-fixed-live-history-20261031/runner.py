import datetime,json,queue,signal,subprocess,threading,time,hashlib,shutil,sqlite3,sys
from pathlib import Path
import httpx
root=Path('/workspace/scratch/installed-graph-fixed-live-history-20261031');root.mkdir(exist_ok=False)
workspace=root/'workspace';python='/workspace/scratch/limited-text-installed-graph-fixed-20261031/bin/python'
report={'classification':'INSTALLED_NEW_WHEEL_PREVIOUS_LIVE_RESULT_COMPATIBILITY_COPY_ONLY_NO_NEW_MODEL' ,'candidate_source':sys.argv[1],'real_model_requests':0,'starts':[],'status':'STARTED'}
def save():(root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def start(new):
 cmd=[python,'-I','-B','-u','-c',"import sys,runpy\ndef audit(event,args):\n if event=='socket.connect' and type(args[1]) is tuple and args[1][0] not in ('127.0.0.1','::1'):raise RuntimeError('Outbound disabled in read-only history compatibility validation')\nsys.addaudithook(audit)\nrunpy.run_module('sim2act.cli',run_name='__main__',alter_sys=True)",'synthetic-workspace','--data-dir',str(workspace),'--exact-read-live']+(['--new'] if new else [])
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

source=Path('/workspace/scratch/exact-read-live-9d74a3a17520-20261031/workspace')
original_db=source/'synthetic-workspace.db'
original_hash=hashlib.sha256(original_db.read_bytes()).hexdigest()
wal=source/'synthetic-workspace.db-wal'
assert not wal.exists() or wal.stat().st_size==0
workspace.mkdir()
for name in ['synthetic-workspace.json','synthetic-workspace.db']:
 shutil.copyfile(source/name,workspace/name)
old=Path('/workspace/scratch/exact-read-live-1a23c032fdc5-20261031')
old_report=json.loads((old/'report.json').read_text())
value=json.loads((old/'saved-run.json').read_text());rid=value['id']
assert value['status']=='SUCCEEDED'
def ledger():
 c=sqlite3.connect('file:'+str(workspace/'synthetic-workspace.db')+'?mode=ro',uri=True)
 c.row_factory=sqlite3.Row
 try:return {t:[dict(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY 1')] for t in ['runs','attempts','reservations','events','run_contracts']}
 finally:c.close()
before=ledger()
assert all(r['status'] in {'SUCCEEDED','FAILED','CANCELLED'} for r in before['runs'])
report.update(original_live_source=old_report['source_commit'],original_live_run=rid,original_db_sha256=original_hash,
 verification_scope='New installed application reading immutable prior terminal results in a private workspace copy; not a new live execution',
 outbound_socket_guard=True,prior_attempts=len(before['attempts']),prior_reservations=len(before['reservations']))
active=None
try:
 for n in range(2):
  active=start(False)
  with httpx.Client(base_url=active[-1]['ready']['url'],headers={'Authorization':'Bearer public-synthetic-blank-workspace'},trust_env=False,timeout=5) as c:
   assert c.get('/').status_code==200
   r=c.get('/api/runs/'+rid);assert r.status_code==200 and r.json()==value
   repeat=c.post('/api/projects/'+old_report['project']+'/runs',json=old_report['request'])
   assert repeat.status_code==202 and repeat.json()['run_id']==rid,(repeat.status_code,repeat.text)
   assert c.get('/api/runs/'+rid).json()==value
  stop(active);active=None
  assert ledger()==before
 assert hashlib.sha256(original_db.read_bytes()).hexdigest()==original_hash
 report.update(status='PASS',run_id=rid,first_reopen_same_result=True,same_key_same_run=True,all_original_five_tables_unchanged=True,
 prior_source_database_unchanged=True,real_model_requests=0,attempt_count_delta=0,reservation_count_delta=0,
 new_result='NOT_EXECUTED',original_result=value['result']['goal_acceptance'])
finally:
 if active is not None:stop(active)
 save();print(json.dumps(report,indent=2))
