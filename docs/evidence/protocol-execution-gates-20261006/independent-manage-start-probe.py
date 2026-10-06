import importlib.util,json,subprocess,sys,time,psutil
from pathlib import Path
spec=importlib.util.spec_from_file_location('manager','/workspace/Sim2Act-pb/scripts/manage.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
summary={'attempts':0,'false_live':[],'exceptions':[]}
for n in range(150):
 command=[sys.executable,'-c','import time; time.sleep(1)']
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin'},start_new_session=True)
 try:
  p=psutil.Process(child.pid); record={'pid':child.pid,'created_at':p.create_time(),'command':command,'kind':'worker','port':0}
  summary['attempts']+=1
  for j in range(3):
   if m.process(record) is None and child.poll() is None:
    summary['false_live'].append({'n':n,'j':j,'status':p.status(),'ctime_delta':p.create_time()-record['created_at'],'argc':len(p.cmdline()),'command_match':p.cmdline()==command})
 except Exception as e:summary['exceptions'].append(type(e).__name__)
 finally:
  child.terminate();child.wait(timeout=3)
Path('/tmp/independent_manage_start_probe.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
