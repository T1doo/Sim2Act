from pathlib import Path
import hashlib,json,re
root=Path('/workspace/Sim2Act/src/sim2act');p=root/'production_trial_admission.py';source=p.read_text();pattern=r'PRODUCTION_QUALIFICATION_HASH = "[a-f0-9]{64}"';assert len(re.findall(pattern,source))==1
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (*root.glob('*.py'),*root.glob('*.c')) if p.name!='config.py'}
files['production_trial_admission.py']=hashlib.sha256(re.sub(pattern,'PRODUCTION_QUALIFICATION_HASH = "'+'0'*64+'"',source).encode()).hexdigest();files['_owned_sql_catalog.json']=hashlib.sha256((root/'_owned_sql_catalog.json').read_bytes()).hexdigest()
m=root/'production_software_qualification.json';proof=json.loads(m.read_text());proof['files']=files;raw=(json.dumps(proof,indent=2,sort_keys=True)+'\n').encode();m.write_bytes(raw);pin=hashlib.sha256(raw).hexdigest();p.write_text(re.sub(pattern,'PRODUCTION_QUALIFICATION_HASH = "'+pin+'"',source));print(json.dumps({'files':len(files),'pin':pin}))
