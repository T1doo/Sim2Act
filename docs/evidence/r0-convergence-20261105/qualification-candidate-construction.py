import hashlib,json,re
from pathlib import Path
root=Path('src/sim2act');evidence=Path('docs/evidence/r0-convergence-20261105')
candidate='3ec03e255c2e146a26f29a7b04912b21e28b0ec1'
for name in ('production_software_qualification.json','text_software_qualification.json'):
 target=evidence/('previous-'+name)
 with target.open('xb') as f:f.write((root/name).read_bytes())
for name in ('production_trial_admission.py','text_continuations.py'):
 p=root/name;s=p.read_text(encoding='utf-8')
 s=s.replace('literal-software-qualification.v1','literal-software-qualification.v2')
 s=s.replace('7e29ffb397d7d7560ebdf617aa345830bc34ee33','653669fcf67965d3b3c8877336b3289746b5d00d').replace('94e60ca3ffe25fc1fdf427f6e31f724c4b2c8dd5',candidate)
 if name=='production_trial_admission.py':
  s=s.replace('{"version", "baseline", "files"}','{"version", "baseline", "review_candidate", "files"}')
  s=s.replace('production-software-qualification.v2','production-software-qualification.v3')
  s=s.replace('and proof["baseline"] == "206153da27edb5353e7106ab52b6e5bcaad86627")','and proof["baseline"] == "206153da27edb5353e7106ab52b6e5bcaad86627"\n            and proof["review_candidate"] == "'+candidate+'")')
 p.write_bytes(s.encode())
files={p.name:p.read_bytes() for pattern in ('*.py','*.c','*.h') for p in root.glob(pattern) if p.name!='config.py'}
files['_owned_sql_catalog.json']=(root/'_owned_sql_catalog.json').read_bytes()
def normalized(data,pin):
 result,count=re.subn((pin+' = "').encode()+b'[0-9a-f]{64}"',(pin+' = "'+'0'*64+'"').encode(),data)
 assert count==1
 return result
def digest(data):return hashlib.sha256(data).hexdigest()
normalized_files=dict(files)
for name,pin in [('production_trial_admission.py','PRODUCTION_QUALIFICATION_HASH'),('text_continuations.py','QUALIFICATION_HASH')]:normalized_files[name]=normalized(files[name],pin)
production={'version':'production-software-qualification.v3','baseline':'206153da27edb5353e7106ab52b6e5bcaad86627','review_candidate':candidate,'files':{k:digest(v) for k,v in normalized_files.items()}}
raw=json.dumps(production,indent=2,sort_keys=True).encode()+b'\n';(root/'production_software_qualification.json').write_bytes(raw)
new_production=re.sub(b'PRODUCTION_QUALIFICATION_HASH = "[0-9a-f]{64}"',('PRODUCTION_QUALIFICATION_HASH = "'+digest(raw)+'"').encode(),files['production_trial_admission.py'])
(root/'production_trial_admission.py').write_bytes(new_production)
text=json.loads((evidence/'previous-text_software_qualification.json').read_bytes())
text.update(version='literal-software-qualification.v2',review_baseline='653669fcf67965d3b3c8877336b3289746b5d00d',review_candidate=candidate)
text['files']={k:digest(new_production if k=='production_trial_admission.py' else normalized_files[k]) for k in files if k.endswith('.py')}
raw=json.dumps(text,indent=2,sort_keys=True).encode()+b'\n';(root/'text_software_qualification.json').write_bytes(raw)
(root/'text_continuations.py').write_bytes(re.sub(b'QUALIFICATION_HASH = "[0-9a-f]{64}"',('QUALIFICATION_HASH = "'+digest(raw)+'"').encode(),files['text_continuations.py']))
print({'status':'CANDIDATE_SEALED_REQUIRES_REGRESSION','production_files':len(production['files']),'text_files':len(text['files'])})
