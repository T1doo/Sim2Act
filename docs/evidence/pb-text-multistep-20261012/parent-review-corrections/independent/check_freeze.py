import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();fp=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
files={p:sha(root/p) for p in sorted(subprocess.check_output(['rg','--files','src','tests'],cwd=root,text=True).splitlines()) if not p.endswith('.pyc')}
impl={p.name:sha(p) for p in sorted((root/'src/sim2act').glob('*.py')) if p.name!='config.py'}
a={'files':files,'count':len(files),'source_map_fingerprint':fp(files),'implementation_count':len(impl),'implementation_fingerprint':fp(impl),'pyproject_sha256':sha(root/'pyproject.toml'),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()}
(out/(sys.argv[1]+'.json')).write_text(json.dumps(a,indent=2)+'\n');print({k:v for k,v in a.items() if k!='files'})
if sys.argv[1]!='source-before':assert a==json.loads((out/'source-before.json').read_text())
