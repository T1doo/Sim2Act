import json,os,subprocess,time
from pathlib import Path
base=Path('/workspace/pa-use-running-clean-install')
root=base/'Sim2Act-local-candidate'
code='import time,json; w=time.monotonic(); c=time.process_time(); import sim2act.api; print(json.dumps({"import_wall_seconds":time.monotonic()-w,"import_cpu_seconds":time.process_time()-c}))'
started=time.monotonic()
result=subprocess.run([str(root/'.venv/bin/python'),'-c',code],cwd=root,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp','PYTHONDONTWRITEBYTECODE':'1'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
(base/'import-timing.log').write_text(result.stdout)
proof={'scope':'Read-only dependency import; no app/Store/Worker/model started','exit_code':result.returncode,'total_wall_seconds':time.monotonic()-started,'module_timing':json.loads(result.stdout) if result.returncode==0 else None}
(base/'import-timing.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
