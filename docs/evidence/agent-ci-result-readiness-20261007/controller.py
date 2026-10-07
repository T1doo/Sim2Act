import importlib.util,pathlib,socket,sys,threading,time,subprocess,json
sys.path.insert(0,str(pathlib.Path.cwd()/'tests'))
spec=importlib.util.spec_from_file_location('agent_fixture',pathlib.Path('scripts/agent-ui/fixture.py'));f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
import uvicorn
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.worker import Worker
root=pathlib.Path('/tmp/sim2act-agent-ci-oracle-review/owned-final');root.mkdir(exist_ok=True)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
f.seed(root,port);store,settings=f.context(root);app=create_app(store,settings)
with TestClient(app) as c:
 c.headers.update({'Authorization':'Bearer synthetic-agent-ui-A'});info=json.loads((root/'info.json').read_text());instances=c.get('/api/internal/apps/'+info['initial_app']+'/instances').json()['items'];assert len(instances)==1;info['iid']=instances[0]['id'];(root/'info.json').write_text(json.dumps(info))
@app.post('/test-only-worker')
def worker():
 assert store.test_only and settings.mode=='mock';assert Worker(store,settings,f.NeverProvider()).once();return {'status':'LOCAL_ONLY'}
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
try:
 end=time.time()+10
 while not server.started:assert thread.is_alive() and time.time()<end;time.sleep(.01)
 r=subprocess.run(['node','/tmp/sim2act-agent-ci-oracle-review/reproduce.cjs',str(root)],capture_output=True,text=True,timeout=40);(root/'driver.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);assert r.returncode==0
finally:
 server.should_exit=True;thread.join(8);assert not thread.is_alive();store.engine.dispose()
