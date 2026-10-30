import gzip,hashlib,json,os
from pathlib import Path
root=Path('/workspace/scratch/graph-edge-stage-20261030')
secret_values={os.environ[k].encode() for k in ('GH_TOKEN','GITHUB_TOKEN','SIM2ACT_INTERN_TOKEN','INTERN_API_TOKEN') if os.environ.get(k)}
assert secret_values
findings=[];decoded=0;files=[]
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.name in ('SHA256SUMS.json','publication-scan.json'):continue
 raw=p.read_bytes();body=gzip.decompress(raw) if p.suffix=='.gz' else raw;decoded+=p.suffix=='.gz'
 if any(v in raw or v in body for v in secret_values):findings.append({'path':str(p.relative_to(root)),'type':'CONFIGURED_SECRET_VALUE'})
 if (b'-----BEGIN '+b'PRIVATE KEY-----') in body or (b'-----BEGIN '+b'RSA PRIVATE KEY-----') in body:findings.append({'path':str(p.relative_to(root)),'type':'PRIVATE_KEY_MARKER'})
 if p.suffix in ('.db','.sqlite','.sqlite3','.pickle','.so','.dll','.exe'):findings.append({'path':str(p.relative_to(root)),'type':'DISALLOWED_RAW_OR_BINARY_ARTIFACT'})
 files.append({'path':str(p.relative_to(root)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
result=dict(status='PASS' if not findings else 'FAIL',checked_files=len(files),gzip_decoded=decoded,configured_secret_values_checked=len(secret_values),findings=findings,scope='Selected project synthetic graph counts/logs/tests/scripts only; no raw DB, model exchange bodies, pickle or binary. Exact currently injected known secrets plus private-key markers; not a universal detector.')
(root/'publication-scan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
assert not findings
files.append({'path':'publication-scan.json','bytes':(root/'publication-scan.json').stat().st_size,'sha256':hashlib.sha256((root/'publication-scan.json').read_bytes()).hexdigest()})
(root/'SHA256SUMS.json').write_text(json.dumps(files,indent=2)+'\n')
