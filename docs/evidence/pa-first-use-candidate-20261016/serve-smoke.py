import json,os,signal,subprocess,time
from pathlib import Path
import httpx
root=Path('/workspace/pa-use-running-clean-install/Sim2Act-local-candidate')
out=Path('/workspace/pa-use-running-clean-install')
receipt=json.loads((root/'synthetic-pa-demo/demo-receipt.json').read_text())
log=out/'serve.log'
with log.open('w') as stream:
 process=subprocess.Popen([str(root/'.venv/bin/python'),'scripts/local_candidate_demo.py','serve','--data-dir','./synthetic-pa-demo','--port','0'],cwd=root,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp','PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+15
  url=None
  while not url:
   lines=log.read_text().splitlines()
   url=next((line.split(': ',1)[1] for line in lines if line.startswith('SYNTHETIC MOCK saved results (read-only): ')),None)
   if process.poll() is not None or time.monotonic()>=deadline: raise RuntimeError('Owned serve startup failed')
   if not url: time.sleep(.05)
  observed=[]
  with httpx.Client(base_url=url,trust_env=False,timeout=60,headers={'Authorization':'Bearer public-synthetic-local-candidate'}) as client:
   paths=['/','/app.js','/use.js','/api/projects','/api/apps?metadata_only=true',receipt['deterministic']['detail'],receipt['natural_pa']['manual_review'],receipt['natural_pa_previous']['manual_review']]
   for path in paths:
    response=client.get(path)
    observed.append({'method':'GET','path':path,'status':response.status_code})
    assert response.status_code==200,(path,response.text)
   families={item['id']:item['use_family'] for item in client.get('/api/apps?metadata_only=true').json()['items']}
   assert families[receipt['natural_pa']['app_id']]=='NATURAL_PA'
   assert receipt['natural_pa']['instance_id']==receipt['natural_pa_previous']['instance_id']
   response=client.post('/api/projects',json={'name':'forbidden'})
   assert response.status_code==405
   observed.append({'method':'POST','path':'/api/projects','status':405})
 finally:
  if process.poll() is None:process.send_signal(signal.SIGINT)
  process.wait(timeout=15)
 assert process.returncode==0,process.returncode
 (out/'serve-smoke.json').write_text(json.dumps({'status':'PASS','source_commit':receipt.get('source_commit','fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675'),'owned_serve_exit_code':process.returncode,'http':observed,'workers_started':0,'real_model_requests':0,'native_browser':'NOT_RUN'},indent=2)+'\n')
 print('PASS owned serve loopback, saved results/manual GET, 405 write guard, SIGINT exit0')
