from pathlib import Path
import gzip,hashlib,json,os,subprocess,sys
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch');source=sys.argv[1]
base=s/('cold-lifecycle-'+source[:8]+'-20261031');meta=Path(str(base)+'-acceptance.json')
r=json.loads(meta.read_text());assert r['status']=='COMPLETED' and r['source_commit']==source and r['default_recovery']['status']=='PASS'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source
assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
out=repo/'docs/evidence/sqlite-commit-boundary-20261031/full-acceptance';out.mkdir();items=[]
def archive(p,name):
 raw=p.read_bytes()
 for key in ('INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN'):
  value=os.environ.get(key,'');assert not value or value.encode() not in raw,'Configured secret found; stop'
 compress=p.suffix in ('.db','.jsonl','.log') or p.name=='use-effective-profile.json'
 data=gzip.compress(raw,mtime=0) if compress else raw;target=out/(name+('.gz' if compress else ''));target.write_bytes(data)
 items.append(dict(file=target.name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),source=str(p),source_sha256=hashlib.sha256(raw).hexdigest()))
archive(meta,meta.name)
for name in ('run-cold-lifecycle-final-acceptance-20261031.py','finish-cold-cancel-after-natural-expiry-20261031.py','archive-cold-lifecycle-acceptance-20261031.py','check-g0-owned-release-reopen-20261031.py','owned_read_pair_profile_20261031.py','cold-lifecycle-'+source[:8]+'-final-acceptance-20261031.log'):
 archive(s/name,name)
for label in ('save','cancel'):
 prefix=Path(str(base)+'-'+label)
 for suffix in ('-run.json','.log','.xml'):archive(Path(str(prefix)+suffix),label+suffix)
 cases={p.resolve().parent for p in prefix.glob('*/snapshot-writer-timings.json')};assert len(cases)==1;case=cases.pop()
 for p in sorted(case.iterdir()):
  if p.suffix=='.db':
   wal=Path(str(p)+'-wal');assert not wal.exists() or wal.stat().st_size==0
  if p.suffix in ('.db','.json','.jsonl'):archive(p,label+'-'+p.name)
 if label=='save':
  for suffix in ('-first-reopen.json','-first-reopen-command.json'):archive(Path(str(prefix)+suffix),'save'+suffix)
recovery=Path(str(base)+'-default-recovery')
for name in ('fixture.db','default-recovery.json'):
 p=recovery/name
 if p.suffix=='.db':
  wal=Path(str(p)+'-wal');assert not wal.exists() or wal.stat().st_size==0
 archive(p,'natural-expiry-'+name)
(out/'archive-manifest.json').write_text(json.dumps(dict(source_commit=source,classification='SYNTHETIC_PYTEST_INPUTS_ONLY_NOT_USER_DATA',configured_secret_exact_value_scan='PASS',items=items),indent=2)+'\n')
print(json.dumps(dict(source=source,files=len(items),destination=str(out),secret_scan='PASS')))
