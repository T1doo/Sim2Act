import subprocess,sys,os,json,hashlib,time
from pathlib import Path
repo=Path('/workspace/Sim2Act-pa-provider');out=Path('/tmp/pa-spec-checklist-author-20261012')
names=subprocess.check_output(['git','ls-files','-z','src','tests','pyproject.toml'],cwd=repo).decode().split('\0')
def snapshot():return {name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in names if name}
before=snapshot();(out/'final-r2-source-before.json').write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
modules=['test_text_continuations.py','test_text_continuation_boundaries.py','test_text_software_qualification.py','test_spec_checklists.py','test_text_workflows.py','test_goal_text_applications.py','test_goal_text_adversarial.py','test_goal_text_rejected_raw.py','test_pa_generation_provider.py','test_pa_material_bindings.py','test_goal_text_ui.py','test_pa_provider_ui.py','test_pa_spec_apps.py','test_pa_spec_ui.py']
cmd=[sys.executable,'-m','pytest',*[str(repo/'tests'/m) for m in modules],'-q','--tb=short','--junitxml='+str(out/'final-r2.xml'),'--basetemp='+str(out/'final-r2-fixtures')]
start=time.time()
with (out/'final-r2.log').open('w') as log:
    result=subprocess.run(cmd,cwd=repo,env={**os.environ,'PYTHONPATH':str(repo/'src')+':'+str(repo/'tests'),'NODE_PATH':'/workspace/node-tools/node_modules'},stdout=log,stderr=subprocess.STDOUT)
after=snapshot();(out/'final-r2-source-after.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
receipt=dict(command=cmd,exit_code=result.returncode,seconds=time.time()-start,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),source_entries=len(before),source_differences=[n for n in before if before[n]!=after[n]])
(out/'final-r2-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print((out/'final-r2.log').read_text()[-3500:]);sys.exit(result.returncode)
