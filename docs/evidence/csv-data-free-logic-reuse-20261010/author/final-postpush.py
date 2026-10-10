import subprocess,json,hashlib,psutil
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/tmp/sim2act-csv-data-free-logic-20261010');out=repo/'docs/evidence/csv-data-free-logic-reuse-20261010'
def git(*a):return subprocess.check_output(['git',*a],cwd=repo,text=True).strip()
head=git('rev-parse','HEAD');source='4a4b6949fd159bd35c1ed1ed9d111426a27b706f';main='6f688e4dd80b5c81d41aecde90e360d3629f9c21'
raw=git('ls-remote','origin','HEAD','refs/heads/main','refs/heads/dev/f1-foundation','refs/heads/dev/csv-data-free-logic-reuse-20261010');remote=dict(line.split('\t')[::-1] for line in raw.splitlines())
assert remote['refs/heads/dev/f1-foundation']==head and remote['refs/heads/dev/csv-data-free-logic-reuse-20261010']==source and remote['refs/heads/main']==remote['HEAD']==main
assert git('branch','--show-current')=='dev/f1-foundation' and git('status','--porcelain=v1')==''
assert git('rev-list','--count','origin/dev/f1-foundation..HEAD')=='0'
assert subprocess.run(['git','merge-base','--is-ancestor',source,head],cwd=repo).returncode==0
changed=git('diff','--name-only',source,head).splitlines();assert changed and all(p.startswith('docs/') for p in changed)
freeze=json.loads((root/'source-freeze-fixed.json').read_text());white=json.loads((out/'COPY_WHITELIST.json').read_text())
items=freeze['files']+[dict(path='docs/evidence/csv-data-free-logic-reuse-20261010/'+f['path'],bytes=f['bytes'],sha256=f['sha256']) for f in white['files']]
p=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for f in items:
    p.stdin.write((head+':'+f['path']+'\n').encode());p.stdin.flush();header=p.stdout.readline().decode().strip().split();assert len(header)==3 and header[1]=='blob',header
    n=int(header[2]);b=p.stdout.read(n);assert p.stdout.read(1)==b'\n';assert n==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
    assert (repo/f['path']).read_bytes()==b,f['path']
p.stdin.close();assert p.wait()==0
locks=[dict(name=x.name,bytes=x.stat().st_size) for x in (repo/'.git').glob('*.lock')];assert locks==[dict(name='codex-index-refresh.lock',bytes=0)]
pending=[x for x in ['MERGE_HEAD','REBASE_HEAD','CHERRY_PICK_HEAD','rebase-merge','rebase-apply','sequencer'] if (repo/'.git'/x).exists()];assert not pending
active=[]
for p in psutil.process_iter(['pid','cmdline']):
    a=p.info['cmdline'] or []
    if any(x.endswith('/pytest') for x in a) and any('/tmp/sim2act-csv-data-free-logic-20261010/' in x for x in a):active.append(p.pid)
assert not active
data=dict(final_dev_sha=head,source_sha=source,remote=remote,clean=True,unpushed_commits=0,non_docs=378,product=72,evidence_objects=white['count'],all_Git_and_working_bytes_exact=True,docs_only_after_source=True,locks=locks,pending_operations=pending,author_test_processes=active,PG=json.loads((root/'pg-cleanup.json').read_text()),PROJECT='PENDING/BLOCKED_PARTIAL',overall='NOT_ACCEPTED',LIVE=0)
(root/'postpush-verification.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items() if k!='PG'}))
