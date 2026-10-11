import datetime,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/tmp/owner-read-order-review-20261011');prefix='sealed-77';command=['/workspace/Sim2Act/.venv/bin/python','-m','pytest','-q','tests/test_owner_acceptance.py','tests/test_goal_text_applications.py','tests/test_goal_text_ui.py','--basetemp='+str(root/(prefix+'-db')),'--junitxml='+str(root/(prefix+'.xml'))]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONPATH='src:tests',NODE_PATH='/workspace/node-tools/node_modules',SIM2ACT_PA_EVIDENCE_DIR=str(root/(prefix+'-pages')))
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
with (root/(prefix+'.log')).open('w') as log:
    p=subprocess.Popen(command,cwd='/workspace/Sim2Act',env=env,stdout=log,stderr=subprocess.STDOUT)
    (root/(prefix+'-process.json')).write_text(json.dumps({'pid':p.pid,'command':command,'started_at':start,'env_constraints':{'database':'isolated SQLite','PYTHONPATH':env['PYTHONPATH'],'NODE_PATH':env['NODE_PATH'],'SIM2ACT_PA_EVIDENCE_DIR':env['SIM2ACT_PA_EVIDENCE_DIR']}},indent=2)+'\n')
    code=p.wait()
r={'command':command,'start':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':code,'elapsed_seconds':time.monotonic()-t,'synthetic_live_model_requests':0,'scope':'35 owner +13 text applications +29 actual HTTP/JSDOM page nodes; no native browser or real semantic owner'}
(root/(prefix+'-result.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));sys.exit(code)
