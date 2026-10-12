import json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path(__file__).parent;name=sys.argv[1]
selection={'pending':['tests/test_text_workflow_pending.py'],'ui':['tests/test_text_workflows_ui.py::test_actual_four_step_text_page_cold_extraction[valid]','tests/test_text_workflows_ui.py::test_actual_four_step_text_page_cold_extraction[late-open-workspace]','tests/test_text_workflows_ui.py::test_actual_four_step_text_page_cold_extraction[late-open-edit]']}[name]
cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*selection,'--basetemp='+str(out/(name+'-fixtures')),'--junitxml='+str(out/(name+'.xml')),'-o','cache_dir='+str(out/(name+'-cache'))]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'tests')+':'+str(root/'src'),'NODE_PATH':'/workspace/node-tools/node_modules','SIM2ACT_TEXT_WORKFLOW_EVIDENCE_DIR':str(out/'ui'),'SIM2ACT_PENDING_EVIDENCE_DIR':str(out/'pending')}
start=time.monotonic()
with (out/(name+'.log')).open('wb') as f:code=subprocess.call(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
a={'command':cmd,'exit_code':code,'wall_seconds':time.monotonic()-start,'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH','SIM2ACT_TEXT_WORKFLOW_EVIDENCE_DIR','SIM2ACT_PENDING_EVIDENCE_DIR']}}
(out/(name+'-exit.json')).write_text(json.dumps(a,indent=2)+'\n');print(json.dumps(a));raise SystemExit(code)
