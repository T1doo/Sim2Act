import hashlib,json,pathlib,subprocess,socket,threading,time,traceback,os,csv,io
from decimal import Decimal
import uvicorn
from sim2act.db import Store,resources,grants,principals,internal_app_runs,internal_instance_data,internal_releases,runs,attempts
from sim2act.config import Settings
from sim2act.api import create_app
from sim2act.worker import Worker
from sqlalchemy import select,event
ROOT=pathlib.Path('/tmp/sim2act-resource-file-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='fdc91282b2107164ba33624246be6f50e007cd13'
def freeze(label):
 manifest=json.loads(pathlib.Path('/tmp/sim2act-resource-file-20261010/source-freeze.json').read_text())['files']; actual={};git={}
 for p,h in manifest.items():
  actual[p]=hashlib.sha256((REPO/p).read_bytes()).hexdigest();git[p]=hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest()
 value={'sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'manifest_count':len(manifest),'worktree_match':actual==manifest,'git_match':git==manifest,'files':actual}
 (ROOT/f'source-{label}.json').write_text(json.dumps(value,indent=2));assert value['worktree_match'] and value['git_match'] and value['sha']==SHA
freeze('before')
old={p:subprocess.check_output(['git','show','66709612d5acd2e4b0dc41f75ef5c9f769508b0c:src/sim2act/web/'+p],cwd=REPO) for p in ['app.js','index.html']}
for p,data in old.items():(ROOT/('old-667-'+p)).write_bytes(data)
(ROOT/'old-source.json').write_text(json.dumps({p:hashlib.sha256(v).hexdigest() for p,v in old.items()},indent=2))
summary=[]
for case in ['business','limits','file-context','lost','uncertain','accepted-aba','read-aba','manual','old-negative']:
 folder=ROOT/case;folder.mkdir(exist_ok=True);url='sqlite:///'+str(folder/'db.sqlite');store=Store(url,test_only=True);store.initialize();owner=store.user('Independent A','independent-A');other=store.user('Independent B','independent-B');a=store.project(owner,'Independent A project');b=store.project(owner,'Independent B project');store.project(other,'Independent foreign project');settings=Settings(url,folder,mode='mock');app=create_app(store,settings)
 raw='label,left,right\r\n"南,区",-0.5,7\r\n北区,2.25,-3\r\n';(folder/'independent.CSV').write_bytes(raw.encode());sql=[]
 def audit(conn,cursor,statement,params,ctx,many):
  if statement.lstrip().split()[0].upper() in ['INSERT','UPDATE','DELETE']:sql.append(statement)
 event.listen(store.engine,'before_cursor_execute',audit)
 @app.post('/independent-worker')
 def tick():
  class Disabled:
   def complete(self,*a,**kw):raise AssertionError('independent provider must never be called')
   request=complete
  return {'worked':Worker(store,settings,Disabled()).once()}
 if case=='old-negative':
  from fastapi.responses import Response
  # Override only the two actual old HTTP assets. Other dependency assets stay exact current bytes.
  app.router.routes=[r for r in app.router.routes if getattr(r,'path',None) not in ['/', '/app.js']]
  @app.get('/')
  def old_index():return Response(old['index.html'],media_type='text/html')
  @app.get('/app.js')
  def old_app():return Response(old['app.js'],media_type='text/javascript')
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()}
 if case=='old-negative':hashes.update(json.loads((ROOT/'old-source.json').read_text()))
 (folder/'config.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','a':a,'b':b,'case':case,'hashes':hashes}))
 server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start();started=time.monotonic()
 try:
  while not server.started:assert time.monotonic()-started<10 and thread.is_alive();time.sleep(.01)
  result=subprocess.run(['node',str(ROOT/'independent.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'})
  (folder/'driver.log').write_text(result.stdout+result.stderr)
  outcome=json.loads((folder/'result.json').read_text());assert result.returncode==0 and outcome['status']=='PASS',(result.returncode,result.stdout,result.stderr)
  with store.tx() as c:
   saved=[dict(r) for r in c.execute(select(resources)).mappings()];g=[dict(r) for r in c.execute(select(grants)).mappings()];rr=[dict(r) for r in c.execute(select(internal_app_runs)).mappings()];data=[dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
   assert c.execute(select(attempts)).first() is None
   if case=='business':
    assert len(saved)==1 and saved[0]['content'].encode()==raw.encode();assert saved[0]['hash']==hashlib.sha256(raw.encode()).hexdigest()
    expected=[sum((Decimal(row[col]) for row in csv.DictReader(io.StringIO(raw))),Decimal(0)) for col in ['left','right']]
    rr=sorted(rr,key=lambda r:r['result_version']);assert len(rr)==2 and len(data)==2;assert [Decimal(r['output']['sum']) for r in rr]==expected;assert [r['result_version'] for r in rr]==[1,2];assert len({r['id'] for r in rr})==2 and all(r['status']=='SUCCEEDED' for r in rr)
    assert len(g)==6 and len(c.execute(select(principals)).all())==5
    assert all(r['output']['resource_id']==saved[0]['id'] for r in rr)
   elif case in ['limits','file-context','old-negative']:assert not saved and not g and not rr and not data
   else:
    expectedcount=5 if case=='uncertain' else 1;assert len(saved)==expectedcount and len(g)==4*expectedcount and not rr and not data
  (folder/'database-evidence.json').write_text(json.dumps({'resources':saved,'grants':g,'app_runs':rr,'data':data,'model_attempts':0},default=str,indent=2));summary.append({'case':case,'status':'PASS','checks':len(outcome['checks']),'pages':len(outcome['pages']),'seconds':time.monotonic()-started})
 except Exception:
  (folder/'failure.log').write_text(traceback.format_exc());summary.append({'case':case,'status':'FAIL','seconds':time.monotonic()-started});print(traceback.format_exc(),flush=True)
 finally:
  server.should_exit=True;thread.join(8);assert not thread.is_alive();(folder/'sql-writes.json').write_text(json.dumps(sql,indent=2));store.engine.dispose()
 print(summary[-1],flush=True)
(ROOT/'summary.json').write_text(json.dumps(summary,indent=2));freeze('after');assert all(x['status']=='PASS' for x in summary)
