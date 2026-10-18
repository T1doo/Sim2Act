import json
import subprocess
from pathlib import Path

repo=Path('/workspace/Sim2Act')
prefix=Path('docs/evidence/pb-first-logic-current-page-20261018')
dest=repo/prefix
out=Path('/workspace/pb-first-logic-current-page-final-delivery-20261018')
out.mkdir(exist_ok=True)
files=sorted(str(p.relative_to(repo)) for p in dest.rglob('*') if p.is_file())
assert files and all(p.startswith(str(prefix)+'/') for p in files)
pathspec=out/'known-new-evidence-pathspec.nul'
pathspec.write_bytes(b'\0'.join(p.encode() for p in files)+b'\0')
records=[]
def call(name,args):
    cmd=['git','-c','core.fsmonitor=false',*args]
    r=subprocess.run(cmd,cwd=repo,capture_output=True,text=True)
    (out/(name+'.stdout')).write_text(r.stdout)
    (out/(name+'.stderr')).write_text(r.stderr)
    records.append(dict(command=cmd,exit_code=r.returncode,stdout=name+'.stdout',stderr=name+'.stderr'))
    (out/'evidence-commit-commands.json').write_text(json.dumps(records,indent=2)+'\n')
    assert r.returncode==0,(name,r.stderr)
    return r.stdout
call('known-evidence-add',['add','-f','--pathspec-from-file='+str(pathspec),'--pathspec-file-nul'])
call('docs-add',['add','docs/F2/Plan.md','docs/F2/PBFirstLogicCurrentPage20261018.md'])
staged=call('staged-paths',['diff','--cached','--name-only']).splitlines()
assert set(staged)==set(files)|{'docs/F2/Plan.md','docs/F2/PBFirstLogicCurrentPage20261018.md'}
call('authored-docs-diff-check',['diff','--cached','--check','--','docs/F2/Plan.md','docs/F2/PBFirstLogicCurrentPage20261018.md',str(prefix/'README.md')])
call('evidence-commit',['commit','-m','docs: record P-B first local logic change current-page acceptance'])
head=call('evidence-head',['rev-parse','HEAD']).strip()
print(json.dumps(dict(head=head,known_evidence_files=len(files),staged_files=len(staged),binary_db_files_explicitly_included=True)))
