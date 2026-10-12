import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path(__file__).parent
freeze=Path('/tmp/pb-text-multistep-author-20261012/frozen-r8.json');j=json.loads(freeze.read_text())
sha=lambda b:hashlib.sha256(b).hexdigest();fp=lambda v:sha(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
files={p:sha((root/p).read_bytes()) for p in j['files']}
impl={p.name:sha(p.read_bytes()) for p in sorted((root/'src/sim2act').glob('*.py')) if p.name!='config.py'}
a={'files':files,'file_count':len(files),'source_map_fingerprint':fp(files),'implementation_files':len(impl),'implementation_fingerprint':fp(impl),'pyproject_sha256':sha((root/'pyproject.toml').read_bytes()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),'differences':[p for p in files if files[p]!=j['files'][p]]}
a['matches']=not a['differences'] and all(a[k]==j[k] for k in ['source_map_fingerprint','implementation_fingerprint','pyproject_sha256','head','branch'])
(out/(sys.argv[1]+'.json')).write_text(json.dumps(a,indent=2)+'\n');print({k:v for k,v in a.items() if k!='files'});assert a['matches']
