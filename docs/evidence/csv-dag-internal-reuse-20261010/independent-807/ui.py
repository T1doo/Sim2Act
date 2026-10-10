from common import *
import socket,threading,time,uvicorn,os,traceback
summary=[]
for case in ['business']:
 folder=ROOT/('ui-corrected-'+case);e=env(folder);start=time.monotonic();server=None
 try:
  aid,rid,p,source=fixture(e);other=request(e,'POST',f'/api/projects/{e[5]}/apps/csv-preview',{'name':'Independent second app','goal':'Navigation isolation','resource_id':rid},201)['id'];app=create_app(e[0],e[1])
  @app.post('/independent-work')
  def execute(body:dict):work(e,body['run_id']);return {'worked':True}
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()}
  (folder/'config.json').write_text(json.dumps({'case':case,'url':f'http://127.0.0.1:{port}','app':aid,'other':other,'source':source,'plan':p,'hashes':hashes}))
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
  while not server.started:assert thread.is_alive() and time.monotonic()-start<15;time.sleep(.01)
  r=subprocess.run(['node',str(ROOT/'independent.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'});(folder/'driver.log').write_text(r.stdout+r.stderr);out=json.loads((folder/'result.json').read_text());assert r.returncode==0 and out['status']=='PASS',(r.returncode,r.stdout,r.stderr)
  with e[0].engine.connect() as c:
   allruns=[dict(x) for x in c.execute(select(internal_app_runs)).mappings()];rows=[dict(x) for x in c.execute(select(internal_instance_data)).mappings()];assert c.execute(select(attempts)).first() is None
   if case=='business':assert [Decimal(x['data']['result']['sum']) for x in sorted(rows,key=lambda r:r['version'])]==[Decimal(4),Decimal('1.5')]
   elif case=='commit-history-aba':assert not allruns
   else:assert len(allruns)==1
  summary.append({'case':case,'status':'PASS','checks':len(out['checks']),'pages':len(out['pages']),'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);summary.append({'case':case,'status':'FAIL','error':err});print(err,flush=True)
 finally:
  if server:server.should_exit=True;thread.join(8);assert not thread.is_alive()
  (folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(summary[-1],flush=True)
(ROOT/'ui-corrected-results.json').write_text(json.dumps(summary,indent=2));freeze('ui-after');assert all(x['status']=='PASS' for x in summary)
