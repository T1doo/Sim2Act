import json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path(__file__).parent;name=sys.argv[1]
modules={'backend':['tests/test_text_workflows.py'],'ui':['tests/test_text_workflows_ui.py'],'independent':[str(out/'test_independent_workflows.py')]}[name]
cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*modules,'--basetemp='+str(out/(name+'-fixtures')),'--junitxml='+str(out/(name+'.xml')),'-o','cache_dir='+str(out/(name+'-cache'))]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'tests')+':'+str(root/'src'),'NODE_PATH':'/workspace/node-tools/node_modules','SIM2ACT_TEXT_WORKFLOW_EVIDENCE_DIR':str(out/'ui'),'INDEPENDENT_TEXT_WORKFLOW_DIR':str(out/'independent-proofs')}
start=time.monotonic()
with (out/(name+'.log')).open('wb') as f:code=subprocess.call(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
r={'command':cmd,'exit_code':code,'wall_seconds':time.monotonic()-start,'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH','SIM2ACT_TEXT_WORKFLOW_EVIDENCE_DIR','INDEPENDENT_TEXT_WORKFLOW_DIR']}}
(out/(name+'-exit.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));sys.exit(code)
