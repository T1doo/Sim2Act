import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

repo=Path('/workspace/Sim2Act')
out=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
records=[]
for n,args in enumerate([['rev-parse','HEAD'],['branch','--show-current'],['status','--porcelain=v1','--untracked-files=all']],1):
    cmd=['git','-c','core.fsmonitor=false',*args]
    r=subprocess.run(cmd,cwd=repo,capture_output=True,text=True,timeout=30)
    (out/f'environment-check-{n}.stdout').write_text(r.stdout)
    (out/f'environment-check-{n}.stderr').write_text(r.stderr)
    records.append(dict(command=cmd,exit_code=r.returncode,stdout=f'environment-check-{n}.stdout',stderr=f'environment-check-{n}.stderr'))
    assert r.returncode==0
    if n==1: assert r.stdout.strip()=='e73004e3529ebfdc27e0105a33f888dbcf042543'
    if n==2: assert r.stdout.strip()=='dev/pb-first-logic-current-page-20261018'
    if n==3: assert r.stdout==''
protected=[]
for label,path in [('ui-draft','/workspace/pb-first-logic-current-page-ui-draft-20261018'),('python-draft','/workspace/pb-first-logic-current-page-tests-draft-20261018')]:
    source=Path(path)
    if source.exists():
        for p in sorted(source.rglob('*')):
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts:
                b=p.read_bytes()
                target=out/'environment-recovery-snapshot'/label/p.relative_to(source)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(b)
                protected.append(dict(path=str(target.relative_to(out)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),scope='IN_PROGRESS_EXTERNAL_DRAFT_NOT_SEALED'))
record=dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(),status='SELECTED_ORIGINAL_ENVIRONMENT_COMMANDS_SUCCEEDED',last_completed_action='normal dev branch creation from verified remote e730; original8fc ancestor and default network verified',checks=records,uncommitted=[],unpushed_commits=[],new_branch_not_pushed_yet=True,owned_product_test_runs_started=0,owned_product_workers_started=0,no_duplicate_process_started=True,unknown_locks_or_processes_modified=False,disk=dict(zip(['total','used','free'],shutil.disk_usage(repo))),external_draft_snapshot=protected,baseline_logs_preserved=True,next_action='continue authorized P-B first local logic current-page work in this selected environment',diagnostic_parser_error='First inline diagnostic used reserved keyword continue as a keyword argument and failed parsing before evaluation. Tool-output excerpt retained separately; no product run or mutation occurred.')
(out/'environment-recovery.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
