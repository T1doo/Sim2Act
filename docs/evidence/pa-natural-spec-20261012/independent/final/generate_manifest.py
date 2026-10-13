from pathlib import Path
import os,json,hashlib,datetime
p=Path(__file__).resolve().parent
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as inp:
  for chunk in iter(lambda:inp.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
items={}
for folder,dirs,files in os.walk(p,followlinks=False):
 dirs.sort();files.sort()
 for name in dirs+files:
  f=Path(folder)/name;key=f.relative_to(p).as_posix()
  if key=='manifest.json':continue
  if f.is_symlink():items[key]={'type':'symlink','target':os.readlink(f)}
  elif f.is_file():items[key]={'type':'file','bytes':f.stat().st_size,'sha256':sha(f)}
d={'version':'independent-evidence-manifest.v1','root':str(p),'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':'82717272e61c2fa174ad8772e54cd9e9eb947c49','entry_count':len(items),'regular_files':sum(v['type']=='file' for v in items.values()),'symlinks':sum(v['type']=='symlink' for v in items.values()),'scope':'all final evidence files/fixture bytes and symlink targets; manifest excluded from itself; prior reports retained separately and checked by history-preservation.json','entries':items}
(p/'manifest.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
# Re-read every recorded byte without modifying the evidence.
diffs=[]
for name,row in items.items():
 f=p/name
 if row['type']=='file':
  if f.stat().st_size!=row['bytes'] or sha(f)!=row['sha256']:diffs.append(name)
 elif not f.is_symlink() or os.readlink(f)!=row['target']:diffs.append(name)
assert not diffs
print(json.dumps({'manifest':str(p/'manifest.json'),'sha256':sha(p/'manifest.json'),'entries':len(items),'regular_files':d['regular_files'],'symlinks':d['symlinks'],'verification_differences':len(diffs),'report_sha256':sha(p/'FINAL_REVIEW.md'),'review_result_sha256':sha(p/'review-result.json')}))
