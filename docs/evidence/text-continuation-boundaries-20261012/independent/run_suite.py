import json, os, subprocess, sys, time
from pathlib import Path
root=Path('/workspace/Sim2Act'); out=Path(__file__).parent
name=sys.argv[1]
modules={'backend':['tests/test_text_continuations.py','tests/test_text_continuation_boundaries.py'],'ui':['tests/test_text_continuation_ui.py'],'independent':[str(out/'test_independent_boundaries.py')]}[name]
cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*modules,'--basetemp='+str(out/(name+'-fixtures')),'--junitxml='+str(out/(name+'.xml')),'-o','cache_dir='+str(out/(name+'-cache'))]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'tests')+':'+str(root/'src'),'NODE_PATH':'/workspace/node-tools/node_modules','SIM2ACT_TEXT_CONTINUATION_EVIDENCE':str(out/'ui'),'SIM2ACT_CONTINUATION_BOUNDARY_DIR':str(out/'boundary-proofs'),'INDEPENDENT_BOUNDARY_DIR':str(out/'independent-proofs')}
start=time.monotonic()
with (out/(name+'.log')).open('wb') as f:
    code=subprocess.call(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
result={'command':cmd,'exit_code':code,'wall_seconds':time.monotonic()-start,'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH','SIM2ACT_TEXT_CONTINUATION_EVIDENCE','SIM2ACT_CONTINUATION_BOUNDARY_DIR','INDEPENDENT_BOUNDARY_DIR']}}
(out/(name+'-exit.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));sys.exit(code)
