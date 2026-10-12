from pathlib import Path
import json, os, subprocess, time
root=Path(__file__).resolve().parent
repo=Path('/workspace/Sim2Act-pa-provider')
args=['/workspace/Sim2Act/.venv/bin/python','-m','pytest','tests/test_pa_spec_apps.py','tests/test_text_software_qualification.py','tests/test_goal_text_rejected_raw.py::test_legacy_shaped_acceptance_remains_readable_without_inventing_raw','tests/test_pa_spec_ui.py','-q','--basetemp='+str(root/'selected-fixtures'),'-o','cache_dir='+str(root/'selected-cache'),'--junitxml='+str(root/'selected.xml')]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules')
start=time.time()
(root/'selected-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH']},'started_at':start},indent=2)+'\n')
with (root/'selected.log').open('w') as log:
 proc=subprocess.run(args,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
result={'returncode':proc.returncode,'wall_seconds':time.time()-start,'started_at':start,'ended_at':time.time(),'args':args}
(root/'selected-exit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(proc.returncode)
