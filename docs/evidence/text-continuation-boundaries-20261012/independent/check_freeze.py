import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path(__file__).parent
freeze=Path('/tmp/text-continuation-boundaries-final-freeze-20261012.json')
j=json.loads(freeze.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
files={p:sha((root/p).read_bytes()) for p in j['source_tests']}
implementation={p.name:sha(p.read_bytes()) for p in sorted((root/'src/sim2act').glob('*.py')) if p.name !='config.py'}
fp=lambda v:sha(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
a={'frozen_count':len(files),'source_tests':files,'map_fingerprint':fp(files),'target_implementation':fp(implementation),'python_implementation_files':len(implementation),'pyproject_sha256':sha((root/'pyproject.toml').read_bytes()),'mismatches':[p for p in files if files[p]!=j['source_tests'][p]],'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()}
a['matches']=not a['mismatches'] and all(a[k]==j[k] for k in ['map_fingerprint','target_implementation','pyproject_sha256'])
(out/(sys.argv[1]+'.json')).write_text(json.dumps(a,indent=2)+'\n')
print({k:v for k,v in a.items() if k!='source_tests'});assert a['matches']
