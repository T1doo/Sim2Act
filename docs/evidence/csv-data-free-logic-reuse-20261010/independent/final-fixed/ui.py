from independent import *
import shutil,socket,threading,uvicorn,os
results=[];base=ROOT/'sqlite-report-run3';source=json.loads((base/'fixture.json').read_text())
for case in ['normal','unknown','identity-ABA','bad-full-plan']:
 folder=ROOT/('ui-'+case+'-corrected');folder.mkdir(exist_ok=True);shutil.copy2(base/'db.sqlite',folder/'db.sqlite');st=h.Store('sqlite:///'+str(folder/'db.sqlite'),test_only=True);settings=h.Settings(st.engine.url.render_as_string(),folder,mode='mock');app=h.create_app(st,settings);server=None;start=time.monotonic();savedgrant=None
 @app.post('/own-target-grant')
 def own_grant(body:dict):
  global savedgrant
  with st.engine.begin() as c:
   if body['action']=='revoke':
    row=c.execute(h.select(h.grants).where(h.grants.c.resource_id==source['material_body']['expected_resource_id'],h.grants.c.principal_id==source['target']['runtime_id'],h.grants.c.tool_ref=='data.aggregate_csv')).mappings().one();savedgrant=dict(row);c.execute(h.update(h.grants).where(h.grants.c.id==row['id']).values(revoked=True))
   elif body['action']=='restore':
    assert savedgrant;c.execute(h.update(h.grants).where(h.grants.c.id==savedgrant['id']).values(**{k:v for k,v in savedgrant.items() if k!='id'}))
   else:raise AssertionError('unknown isolated fixture hook')
  return {'ownfixture':True}
 try:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()};(folder/'config.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','case':case,'project':source['logic']['project_id'],'logic':source['logic']['id'],'app':source['target']['id'],'resource':source['material_body']['expected_resource_id'],'originalResource':source['source']['rid'],'originalApp':source['source']['app']['id'],'hashes':hashes}))
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
  while not server.started:assert thread.is_alive() and time.monotonic()-start<15;time.sleep(.01)
  run=subprocess.run(['node',str(ROOT/'independent-ui.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'});(folder/'driver.log').write_text(run.stdout+run.stderr);out=json.loads((folder/'UI_RESULT.json').read_text());assert run.returncode==0 and out['status']=='PASS',(run.returncode,run.stderr);results.append({'case':case,'status':'PASS','checks':len(out['checks']),'pages':len(out['pages']),'seconds':time.monotonic()-start})
 except Exception:
  error=traceback.format_exc();(folder/'UI_HARNESS_OR_CASE_FAILURE.log').write_text(error);results.append({'case':case,'status':'FAIL','error':error});print(error,flush=True)
 finally:
  if server:server.should_exit=True;thread.join(8);assert not thread.is_alive()
  with st.engine.connect() as c:data={t.name:[dict(x) for x in c.execute(h.select(t)).mappings()] for t in h.meta.sorted_tables}
  (folder/'database-evidence.json').write_text(json.dumps(data,indent=2,default=str));st.engine.dispose()
 print(results[-1],flush=True)
(ROOT/'UI_RESULTS.json').write_text(json.dumps(results,indent=2));assert all(x['status']=='PASS' for x in results)
