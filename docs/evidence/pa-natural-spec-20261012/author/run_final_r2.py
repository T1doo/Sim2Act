"""Actual complete rerun with explicit local dependencies and source closure."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act-pa-provider')
FROZEN = 'c28e91a5066e59c1c36e76b910515298d0d1eb28'

def dump(name, value):
    (ROOT / name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

def source_map():
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    names = subprocess.check_output(['git','ls-files','-z','src','tests','pyproject.toml'],cwd=REPO).decode().split('\0')
    files = {name:hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in names if name}
    assert len(files) == 434
    return dict(head=head,files=files,selection='all git-tracked src/tests/fixtures/pyproject; no suffix exclusion')

before = source_map()
assert before['head'] == FROZEN and not subprocess.check_output(['git','status','--porcelain'],cwd=REPO).strip()
dump('final-r2-source-before.json',before)
selected = ['tests/test_natural_spec_apps.py','tests/test_pa_natural_spec_ui.py','tests/test_pa_spec_apps.py',
            'tests/test_pa_spec_ui.py','tests/test_text_software_qualification.py','tests/test_goal_text_applications.py',
            'tests/test_goal_text_adversarial.py','tests/test_goal_text_rejected_raw.py','tests/test_pa_material_bindings.py',
            'tests/test_bounded_agent_apps.py']
selected += ['tests/test_goal_text_ui.py::test_goal_text_offline_page_actual_worker['+case+']' for case in
             ['valid','lost-generation','lost-confirm','late-confirm-edit-undo','late-confirm-read-edit-undo']]
args = ['/workspace/Sim2Act/.venv/bin/python','-m','pytest','-q',*selected,
        '--basetemp='+str(ROOT/'final-r2-tmp'),'-o','cache_dir='+str(ROOT/'final-r2-cache'),
        '--junitxml='+str(ROOT/'final-r2.xml')]
env = dict(os.environ)
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
env.update(PYTHONPATH=str(REPO/'src')+':'+str(REPO/'tests'),PYTHONDONTWRITEBYTECODE='1',
           NODE_PATH='/workspace/node-tools/node_modules')
started = time.time()
dump('final-r2-command.json',dict(args=args,cwd=str(REPO),started_at=started,
     safe_environment={k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE','NODE_PATH']},
     sqlite_only='SIM2ACT_TEST_DATABASE_URL removed without reading or printing its value'))
with (ROOT/'final-r2.log').open('w') as stdout,(ROOT/'final-r2.stderr').open('w') as stderr:
    process = subprocess.run(args,cwd=REPO,env=env,stdout=stdout,stderr=stderr)
ended = time.time()
after = source_map()
differences = {name:[before['files'].get(name),after['files'].get(name)] for name in
               set(before['files'])|set(after['files']) if before['files'].get(name)!=after['files'].get(name)}
after['differences'] = differences
dump('final-r2-source-after.json',after)
receipt = dict(exit_code=process.returncode,started_at=started,ended_at=ended,wall_seconds=ended-started,
               frozen_head=FROZEN,head_after=after['head'],source_entries=len(after['files']),source_differences=len(differences))
dump('final-r2-process-exit.json',receipt)
print(json.dumps(receipt,indent=2))
assert after['head'] == FROZEN and not differences
raise SystemExit(process.returncode)
