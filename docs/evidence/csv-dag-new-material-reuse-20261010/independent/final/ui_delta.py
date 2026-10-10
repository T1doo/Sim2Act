from common import *
import socket,threading,time,uvicorn,os,shutil,traceback
base=ROOT/'positive-report';cfg=json.loads((base/'fixture.json').read_text());results=[]
for case in ['late-accepted-aba']:
 folder=ROOT/('ui-'+case);folder.mkdir(exist_ok=True);shutil.copy2(base/'baseline.sqlite',folder/'db.sqlite');url='sqlite:///'+str(folder/'db.sqlite');st=Store(url,test_only=True);settings=Settings(url,folder,mode='mock');app=create_app(st,settings);server=None;start=time.monotonic()
 try:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()};(folder/'config.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','case':case,'source':cfg['source_app'],'target':cfg['target_app']['id'],'release':cfg['release'],'hashes':hashes}))
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
  while not server.started:assert thread.is_alive() and time.monotonic()-start<15;time.sleep(.01)
  run=subprocess.run(['node',str(ROOT/'ui_independent.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'});(folder/'driver.log').write_text(run.stdout+run.stderr);out=json.loads((folder/'result.json').read_text());assert run.returncode==0 and out['status']=='PASS',(run.returncode,run.stderr)
  with st.engine.connect() as c:
   assert c.execute(select(attempts)).first() is None
   assert len(c.execute(select(runs)).all())==2 # original source and old instance only
   assert len(c.execute(select(internal_instances)).all())==1
  results.append({'case':case,'status':'PASS','checks':len(out['checks']),'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','error':err});print(err,flush=True)
 finally:
  if server:server.should_exit=True;thread.join(8);assert not thread.is_alive()
  with st.engine.connect() as c:data={t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in meta.sorted_tables}
  (folder/'database-evidence.json').write_text(json.dumps(data,indent=2,default=str));st.engine.dispose()
 print(results[-1],flush=True)
(ROOT/'UI_DELTA_RESULTS.json').write_text(json.dumps(results,indent=2));freeze('ui-delta-after');assert all(x['status']=='PASS' for x in results)
