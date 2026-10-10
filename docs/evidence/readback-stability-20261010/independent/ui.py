from common import *
from conftest import env as original
from test_conditional_run_bindings import env as bounded
from test_report_presentations import prepared
import uvicorn,socket,threading,contextvars
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None);results=[]
for case in ['late-check','lost-check']:
 folder=ROOT/('ui-'+case);folder.mkdir(exist_ok=True);gen=original.__wrapped__(folder);e=bounded.__wrapped__(next(gen));server=None;start=time.monotonic()
 try:
  app,_,_,_,output,wires=prepared(e,folder,peer=True);service=create_app(e[0],e[1]);context=contextvars.ContextVar('private-request',default=None);mutations=[]
  @service.middleware('http')
  async def scope(request,call_next):
   mark=context.set((request.method,request.url.path))
   try:return await call_next(request)
   finally:context.reset(mark)
  def audit(c,cursor,statement,params,ctx,many):
   if statement.lstrip().split()[0].upper() in ['INSERT','UPDATE','DELETE']:mutations.append({'request':context.get(),'statement':statement})
  event.listen(e[0].engine,'before_cursor_execute',audit);before=state(e[0])
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'src/sim2act/web').iterdir() if p.is_file()};(folder/'config.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','app':app['id'],'text':output['explanation'],'case':case,'hashes':hashes}))
  server=uvicorn.Server(uvicorn.Config(service,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
  while not server.started:assert thread.is_alive() and time.monotonic()-start<12;time.sleep(.01)
  run=subprocess.run(['node',str(ROOT/'independent-ui.cjs'),str(folder)],capture_output=True,text=True,timeout=90,env={**os.environ,'NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules'});(folder/'driver.log').write_text(run.stdout+run.stderr);out=json.loads((folder/'result.json').read_text());assert run.returncode==0 and out['status']=='PASS',(run.returncode,run.stdout,run.stderr)
  after=state(e[0]);assert all(before[k]==after[k] for k in before if not k.startswith('delivery_graph_'));assert not any(m['request'] and m['request'][0]=='GET' for m in mutations);assert len(wires)==4;results.append({'case':case,'status':'PASS','checks':len(out['checks']),'pages':len(out['pages']),'seconds':time.monotonic()-start,'mock_exchanges':len(wires)})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','error':err});print(err,flush=True)
 finally:
  if server:server.should_exit=True;thread.join(8);assert not thread.is_alive()
  if 'audit' in locals():event.remove(e[0].engine,'before_cursor_execute',audit)
  (folder/'mutations.json').write_text(json.dumps(mutations,indent=2));(folder/'database-evidence.json').write_text(json.dumps(state(e[0]),indent=2,default=str));gen.close()
 print(results[-1],flush=True)
(ROOT/'ui-results.json').write_text(json.dumps(results,indent=2));freeze('ui-after');assert all(r['status']=='PASS' for r in results)
