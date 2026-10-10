from common import *
import shutil,socket,threading,uvicorn,os,time,traceback
OLD=Path('/tmp/sim2act-dag-new-csv-independent-20261010/final') if False else pathlib.Path('/tmp/sim2act-dag-new-csv-independent-20261010/final');results=[]
for family,case in [('v1','normal-v1'),('report','normal-report'),('report','bad-ID'),('report','bad-input'),('report','readback503')]:
 base=OLD/('business-'+family);response=json.loads((base/'response.json').read_text());i=response['newinstance'];rel=response['newrelease'];folder=ROOT/case;folder.mkdir(exist_ok=True);shutil.copy2(base/'db.sqlite',folder/'db.sqlite');url='sqlite:///'+str(folder/'db.sqlite');st=Store(url,test_only=True);settings=Settings(url,folder,mode='mock');app=create_app(st,settings);server=None;start=time.monotonic()
 @app.post('/own-work')
 def own_work(body:dict):
  e=[st,settings,None,None,None,None,None];work(e,body['run_id']);return {'worked':True}
 try:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()};(folder/'config.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','case':case,'app':i['source_app_id'],'instance':i['id'],'resource':rel['snapshot']['draft']['candidate']['manifest']['data_bindings'][0]['resource_ref'],'sourceHash':rel['snapshot']['execution_source']['source_hash'],'report':family=='report','hashes':hashes}))
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
  while not server.started:assert thread.is_alive() and time.monotonic()-start<15;time.sleep(.01)
  run=subprocess.run(['node',str(ROOT/'independent.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'});(folder/'driver.log').write_text(run.stdout+run.stderr);out=json.loads((folder/'result.json').read_text());assert run.returncode==0 and out['status']=='PASS',(run.returncode,run.stderr)
  with st.engine.connect() as c:
   rows=c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).mappings().all();assert len(rows)==(1 if case=='bad-ID' else 2);assert c.execute(select(attempts)).first() is None
  results.append({'case':case,'status':'PASS','checks':len(out['checks']),'pages':len(out['pages']),'seconds':time.monotonic()-start})
 except Exception:
  error=traceback.format_exc();(folder/'failure.log').write_text(error);results.append({'case':case,'status':'FAIL','error':error});print(error,flush=True)
 finally:
  if server:server.should_exit=True;thread.join(8);assert not thread.is_alive()
  with st.engine.connect() as c:data={t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in meta.sorted_tables}
  (folder/'database-evidence.json').write_text(json.dumps(data,indent=2,default=str));st.engine.dispose()
 print(results[-1],flush=True)
(ROOT/'UI_RESULTS.json').write_text(json.dumps(results,indent=2));assert all(x['status']=='PASS' for x in results)
