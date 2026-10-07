import importlib.util,json,sys,socket,threading,time,subprocess,os
from pathlib import Path
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker
import uvicorn
root=Path(sys.argv[1]);root.mkdir(exist_ok=True)
store=Store('sqlite:///'+str(root/'fixture.db'),test_only=True);settings=Settings(str(store.engine.url),root,mode='mock')
spec=importlib.util.spec_from_file_location('windows_fixture','scripts/windows_browser_ci.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if len(sys.argv)>2:
 info=json.loads((root/'info.json').read_text())
 if sys.argv[2]=='worker':assert Worker(store,settings).once()
 print(json.dumps(module.task_history_snapshot(store,info)));sys.exit()
store.initialize();a=store.user('SYNTHETIC browser A','synthetic-browser-A');b=store.user('SYNTHETIC browser B','synthetic-browser-B')
store.project(a,'SYNTHETIC browser A');store.project(b,'SYNTHETIC browser B');project=store.project(a,'SYNTHETIC task history A');other=store.project(a,'SYNTHETIC task history other owned');resource=store.resource(a,project,'synthetic-task.csv','csv','amount\n10\n30\n')
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
info={'base':f'http://127.0.0.1:{port}','project':project,'other':other,'resource':resource,'other_identity_name':'SYNTHETIC browser B'};(root/'info.json').write_text(json.dumps(info))
server=uvicorn.Server(uvicorn.Config(create_app(store,settings),host='127.0.0.1',port=port,access_log=False,log_level='error'));thread=threading.Thread(target=server.run);thread.start()
try:
 while not server.started:time.sleep(.02)
 result=subprocess.run(['node','/tmp/task_history_module_offline.cjs',str(root),sys.executable]);sys.exit(result.returncode)
finally:server.should_exit=True;thread.join(timeout=5)
