"""Only exact duplicate evidence copies in one own disposable baseline; originals stay."""
import datetime,hashlib,json,os,stat,subprocess,time
from pathlib import Path
repo=Path('/workspace/Sim2Act'); root=Path('/workspace/scratch/g0-baseline-024354f1-20261031/docs/evidence')
out=repo/'docs/evidence/locked-runtime-live-controller-20261101'; log=out/'cleanup.json'
assert not log.exists() and root.is_dir() and not root.is_symlink()
assert not (root.parents[1]/'.git').exists()
for proc in Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 for link in [proc/'cwd',*(proc/'fd').glob('*')]:
  try:t=os.readlink(link)
  except OSError:continue
  assert t!=str(root) and not t.startswith(str(root)+'/'), 'duplicate evidence in use'
 # Reject even memory mappings of a currently closed fd.
 try:m=(proc/'maps').read_text()
 except OSError:continue
 assert str(root) not in m, 'duplicate evidence memory mapped'
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
tracked=set(subprocess.check_output(['git','ls-files','-z','docs/evidence'],cwd=repo).decode().split('\0'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
before=os.statvfs(repo).f_bavail*os.statvfs(repo).f_frsize
value=dict(kind='OWNED_BASELINE_EXACT_DUPLICATE_EVIDENCE_ONLY',started=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_head=head,temporary_root=str(root),original_root=str(repo/'docs/evidence'),space_before=before,entries=[],preserved='all original tracked evidence, source, Git, final packages, manifests, unique/unmatched files, dependencies, failures and unknowns',status='VERIFYING')
log.write_text(json.dumps(value,indent=2)+'\n')
# Large known copied archives first; at most 2.5GiB, stop once >=2.5GiB free.
candidates=sorted((p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and p.stat().st_size>=1024**2),key=lambda p:p.stat().st_size,reverse=True)
for p in candidates:
 st=p.stat(); rel=p.relative_to(root); original=repo/'docs/evidence'/rel
 if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or not original.is_file() or original.is_symlink():continue
 if ('docs/evidence/'+str(rel)) not in tracked or original.stat().st_size!=st.st_size:continue
 # Exclude any declared release/package/inventory manifests, even duplicate ones.
 if any(x in p.name.lower() for x in ('manifest','inventory','wheel','portable','installer')):continue
 digest=sha(p)
 if digest!=sha(original):continue
 current=p.stat()
 if (current.st_ino,current.st_size,current.st_mtime_ns)!=(st.st_ino,st.st_size,st.st_mtime_ns):raise RuntimeError('copy changed during verification')
 # Original is hashed immediately before unlink; no primary or Git write occurs.
 item=dict(copy=str(p),original=str(original),bytes=st.st_size,sha256=digest,copy_mode=oct(st.st_mode&0o777),restore='copy original bytes to exact copy path after verifying recorded SHA256',deleted=False)
 value['entries'].append(item);log.write_text(json.dumps(value,indent=2)+'\n')
 p.unlink();item['deleted']=True;log.write_text(json.dumps(value,indent=2)+'\n')
 if os.statvfs(repo).f_bavail*os.statvfs(repo).f_frsize>=int(3.25*1024**3):break
value.update(status='COMPLETE',finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),space_after=os.statvfs(repo).f_bavail*os.statvfs(repo).f_frsize,deleted_copies=sum(x['deleted'] for x in value['entries']),deleted_bytes=sum(x['bytes'] for x in value['entries'] if x['deleted']))
log.write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:value[k] for k in ['status','deleted_copies','deleted_bytes','space_before','space_after']}))
