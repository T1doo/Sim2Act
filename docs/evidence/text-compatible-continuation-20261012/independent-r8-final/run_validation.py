import json,os,subprocess,sys,time
from pathlib import Path
base=Path('/tmp/text-continuation-independent-final-v3-20261012')
name=sys.argv[1]
modules={'backend':'tests/test_text_continuations.py','ui':'tests/test_text_continuation_ui.py','adversarial':str(base/'test_adversarial.py'),'ui-adversarial':str(base/'test_ui_adversarial.py'),'terminal-history':str(base/'test_terminal_history.py')}
cmd=['.venv/bin/python','-m','pytest',modules[name],'-q','--basetemp='+str(base/(name+'-fixtures')),'--junitxml='+str(base/(name+'.xml')),'-o','cache_dir='+str(base/(name+'-cache'))]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/workspace/Sim2Act/tests:/workspace/Sim2Act/src',NODE_PATH='/workspace/node-tools/node_modules',SIM2ACT_TEXT_CONTINUATION_EVIDENCE=str(base/'ui'),SIM2ACT_INDEPENDENT_ADVERSARIAL_EVIDENCE=str(base/'adversarial'),SIM2ACT_INDEPENDENT_UI_EVIDENCE=str(base/'ui-adversarial'))
t=time.monotonic()
with (base/(name+'.log')).open('w') as log:
 p=subprocess.run(cmd,cwd='/workspace/Sim2Act',env=env,stdout=log,stderr=subprocess.STDOUT)
value={'command':cmd,'exit_code':p.returncode,'wall_seconds':time.monotonic()-t}
(base/(name+'-exit.json')).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
sys.exit(p.returncode)
