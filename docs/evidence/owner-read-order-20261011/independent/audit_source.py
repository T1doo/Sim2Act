import hashlib,json,subprocess,sys
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/tmp/owner-read-order-review-20261011');phase=sys.argv[1]
f=repo/'docs/evidence/owner-read-order-20261011/final-source-freeze.json'
m=json.loads(f.read_text());actual={p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in m['sha256']}
wrong=[p for p,h in m['sha256'].items() if actual[p]!=h]
old=json.loads((out/'prior-owner-evidence-baseline.json').read_text())
paths=subprocess.run(['git','ls-tree','-r','--name-only','ed5cda2e341f0601879ad3f1e42ad1667022d490','--','docs/evidence/owner-version-acceptance-20261011'],cwd=repo,capture_output=True,text=True,check=True).stdout.splitlines()
prior=[]
for p in paths:
    expected=subprocess.run(['git','show','ed5cda2e341f0601879ad3f1e42ad1667022d490:'+p],cwd=repo,capture_output=True,check=True).stdout
    current=(repo/p).read_bytes()
    if current!=expected:prior.append(p)
r={'phase':phase,'source_count':len(actual),'freeze_manifest_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'source_sha256':actual,'source_mismatches':wrong,'prior_owner_evidence_tracked_count':len(paths),'prior_owner_evidence_mismatches':prior,'prior_check':'byte identity against ed5 Git blobs, not test rerun'}
(out/('sealed-source-'+phase+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
if phase=='before':(out/'final-source-freeze.json').write_bytes(f.read_bytes())
print(json.dumps({'source_count':len(actual),'source_mismatch_count':len(wrong),'prior_owner_evidence_count':len(paths),'prior_mismatch_count':len(prior),'manifest_sha256':r['freeze_manifest_sha256']}))
assert not wrong and not prior
