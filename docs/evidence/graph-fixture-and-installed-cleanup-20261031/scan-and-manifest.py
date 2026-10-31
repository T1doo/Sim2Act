import hashlib,io,json,os,zipfile
from pathlib import Path
repo=Path('/workspace/Sim2Act')
evidence=repo/'docs/evidence/graph-fixture-and-installed-cleanup-20261031'
deliver=repo/'deliverables/limited-text-candidate-graph-fixed-20261031'
secrets=[os.environ[n].encode() for n in ['INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN','GH_TOKEN','GITHUB_TOKEN'] if os.environ.get(n)]
count=0;members=0;total=0;problems=[]
def inspect(raw,label,depth=0):
 global members,total
 total+=len(raw)
 if any(secret in raw for secret in secrets):problems.append({'path':label,'type':'CURRENT_CONFIGURED_SECRET_MATCH'})
 if depth<3 and raw[:4]==b'PK\x03\x04':
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=z.namelist()
   assert len(names)==len(set(names))
   for name in names:
    assert not name.startswith('/') and '..' not in Path(name).parts
    members+=1
    inspect(z.read(name),label+'!'+name,depth+1)
files=[repo/'README.md']+sorted(p for d in [evidence,deliver] for p in d.rglob('*') if p.is_file() and p.name not in {'artifact-manifest.json','privacy-check.json'})
for p in files:
 assert not p.is_symlink()
 assert not p.name.endswith(('.db','.sqlite','.db-wal','.db-shm','.env','.pem','.key'))
 count+=1;inspect(p.read_bytes(),str(p.relative_to(repo)))
report={'candidate_source':'2d41ad38b84630cb817d87374122bce31e357d0d','files_scanned':count,'nested_zip_wheel_members_scanned':members,'decoded_bytes_scanned':total,'configured_secret_matches':len(problems),'problems':problems,'database_or_private_configuration_files_in_new_evidence':False,'content_provenance':'Only task-generated synthetic fixtures/text/CSV, controlled package sources, test diagnostics, hashes and copy-only prior synthetic Run result','prior_original_database_distributed_in_this_change':False,'secret_values_printed':False}
(evidence/'privacy-check.json').write_text(json.dumps(report,indent=2)+'\n')
assert not problems,'Secret match: inspect path/type privately before any commit'
all_files=[repo/'README.md']+sorted(p for d in [evidence,deliver] for p in d.rglob('*') if p.is_file() and p.name!='artifact-manifest.json')
manifest={'candidate_source':report['candidate_source'],'files':{str(p.relative_to(repo)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in all_files}}
(evidence/'artifact-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['files_scanned','nested_zip_wheel_members_scanned','configured_secret_matches','database_or_private_configuration_files_in_new_evidence']}))
