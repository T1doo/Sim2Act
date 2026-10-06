import importlib.util,json,subprocess,sys,time,psutil
from pathlib import Path
spec=importlib.util.spec_from_file_location('manager','/workspace/Sim2Act-pb/scripts/manage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
result={'attempts':0,'witness':None}
for n in range(500):
 command=[sys.executable,'-c','import time;time.sleep(3)']
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin'},start_new_session=True)
 try:
  p=psutil.Process(child.pid);r={'pid':child.pid,'created_at':p.create_time(),'command':command,'kind':'worker','port':0};result['attempts']+=1
  if m.process(r) is None and child.poll() is None:
   initial={'running':p.is_running(),'status':p.status(),'ctime_match':p.create_time()==r['created_at'],'manager_denied':True}
   # Actual manager.stop behavior while cmdline is still empty; no other PID is touched.
   initial['alive_before_wait']=child.poll() is None
   deadline=time.monotonic()+1
   while time.monotonic()<deadline and child.poll() is None and p.cmdline()!=command:time.sleep(.001)
   result['witness']={'initial':initial,'eventual_command_match':p.cmdline()==command,'eventual_manager_accepts':m.process(r) is not None,'still_alive':child.poll() is None};break
 finally:
  if child.poll() is None:child.terminate()
  child.wait(timeout=3)
Path('/tmp/independent_manage_empty_probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
