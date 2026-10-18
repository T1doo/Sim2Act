import datetime
import hashlib
import json
import subprocess
from pathlib import Path

repo=Path('/workspace/Sim2Act')
raw=Path('/workspace/pa-current-unseen-flow-evidence-20261018')
evidence=repo/'docs/evidence/pa-current-unseen-flow-20261018'
out=Path('/workspace/pa-current-unseen-flow-final-delivery-20261018')
out.mkdir(exist_ok=True)
branch='dev/pa-unseen-input-current-page-20261018'
baseline='304bff97584ac157d56597f5ab52ea7f5ecb1d9f'
def git(*args):
    r=subprocess.run(['git','-c','core.fsmonitor=false',*args],cwd=repo,capture_output=True,text=True,timeout=90)
    assert r.returncode==0,(args,r.stderr)
    return r.stdout
def sha(b):
    return hashlib.sha256(b).hexdigest()
def refs(s):
    return dict((parts[1],parts[0]) for line in s.splitlines() if (parts:=line.split()))
head=git('rev-parse','HEAD').strip()
source=json.loads((raw/'inputs-after.json').read_text())
summary=json.loads((raw/'qualification-summary.json').read_text())
assert source['head']==summary['execution']['head']=='fddccd09a72d628cdb0ea382009c84545a29cb9f'
before=refs((raw/'baseline-4.stdout').read_text())
remote_text=git('ls-remote','--refs','origin')
(out/'remote-final.txt').write_text(remote_text)
remote=refs(remote_text)
own='refs/heads/'+branch
assert own not in before and remote[own]==head
assert {k:v for k,v in remote.items() if k!=own}==before
assert git('branch','--show-current').strip()==branch
assert not git('status','--porcelain=v1','--untracked-files=all')
assert git('rev-list','--left-right','--count','HEAD...origin/'+branch).split()==['0','0']
assert not git('log','--format=%H','origin/'+branch+'..HEAD').strip()
for ancestor in ['8fc70cc43a6ac81cd522249e8a3d367cd66c9238',baseline,source['head']]:
    git('merge-base','--is-ancestor',ancestor,head)
assert not git('diff','--name-only',baseline,head,'--','src/').strip()
post_source=git('diff','--name-only',source['head'],head).splitlines()
assert post_source and all(x.startswith('docs/') for x in post_source)
for path,record in source['inputs'].items():
    data=(repo/path).read_bytes()
    assert len(data)==record['bytes'] and sha(data)==record['sha256'],path
checks={}
for line in (evidence/'SHA256SUMS').read_text().splitlines():
    digest,path=line.split('  ',1)
    assert sha((evidence/path).read_bytes())==digest,path
    checks[path]=digest
files=sorted((p for p in evidence.rglob('*') if p.is_file()),key=lambda p:str(p.relative_to(repo)))
assert set(checks)=={str(p.relative_to(evidence)) for p in files if p.name!='SHA256SUMS'}
tracked=git('ls-files','--',str(evidence.relative_to(repo))).splitlines()
assert tracked==[str(p.relative_to(repo)) for p in files]
batch=subprocess.Popen(['git','-c','core.fsmonitor=false','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    for path in files:
        relative=str(path.relative_to(repo))
        batch.stdin.write(('HEAD:'+relative+'\n').encode());batch.stdin.flush()
        header=batch.stdout.readline().decode().split()
        assert len(header)==3 and header[1]=='blob',(relative,header)
        data=batch.stdout.read(int(header[2]));assert batch.stdout.read(1)==b'\n'
        assert data==path.read_bytes(),relative
finally:
    batch.stdin.close()
    batch.wait(timeout=30)
assert batch.returncode==0
sealed=Path('/workspace/product-critical-path-triage-independent-20261018')
seal=json.loads((sealed/'sealed-manifest.json').read_text())
rows=seal['files'] if isinstance(seal,dict) and 'files' in seal else seal
if isinstance(rows,dict):
    rows=[dict(path=k,**v) for k,v in rows.items()]
for row in rows:
    data=(sealed/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256']
    assert data==(evidence/'originals/independent'/row['path']).read_bytes()
package=json.loads((evidence/'package-summary.json').read_text())
result=dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(),head=head,remote_sha=remote[own],
    actual_execution_sha=source['head'],baseline_sha=baseline,branch=branch,
    local_remote_left_right=[0,0],uncommitted=[],unpushed=[],remote_other_refs_unchanged=len(before),
    remote_new_refs=[own],main_unchanged=True,execution_inputs=source['input_count'],production_inputs=source['production_count'],
    final_execution_input_drift=[],production_changes_from_baseline=[],post_frozen_source_docs_only=True,
    evidence_git_blobs_verified=len(files),checksum_entries_verified=len(checks),
    independent_sealed_originals_verified=len(rows),independent_manifest_sha256=sha((sealed/'sealed-manifest.json').read_bytes()),
    raw_files=package['raw_files'],raw_bundle_sha256=package['bundle_sha256'],
    unique_final_tests=summary['unique_pytest_nodes'],total_executions=summary['executions'],
    retained_failures=summary['failed_executions'],mock_requests=summary['total_mock_requests'],real_model_requests=0,
    qualification='LIMITED_CURRENT_PA_FULL_PAGE_MOCK_WITH_SIMULATED_OWNER_DECISION',
    old_full_disk_independent_report_gap='NOT_RECOVERED',old_exit139_cause='UNKNOWN',cancelled_installation_digest_window='NOT_VERIFIED')
(out/'final-delivery-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
