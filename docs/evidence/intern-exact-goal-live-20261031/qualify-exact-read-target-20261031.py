"""Freeze the reviewed current target, with two exact literal roles, no filename exemptions."""
import ast,hashlib,json,re
from pathlib import Path
root=Path('/workspace/Sim2Act/src/sim2act')
def normalize(raw,name):
 tree=ast.parse(raw)
 nodes=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name]
 assert len(nodes)==1 and isinstance(nodes[0].value,ast.Constant)
 old=nodes[0].value.value;assert type(old) is str and re.fullmatch('[a-f0-9]{64}',old)
 literal=f'{name} = "{old}"'.encode();assert raw.count(literal)==1
 return raw.replace(literal, (name + ' = "' + '0' * 64 + '"').encode()), old
# First production, binding both role-normalized source files and all existing C/h/catalog.
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*root.glob('*.py'),*root.glob('*.c'),*root.glob('*.h')] if p.name!='config.py'}
for file,name in [('production_trial_admission.py','PRODUCTION_QUALIFICATION_HASH'),('text_continuations.py','QUALIFICATION_HASH')]:
 raw=(root/file).read_bytes();normalized,old=normalize(raw,name);files[file]=hashlib.sha256(normalized).hexdigest()
files['_owned_sql_catalog.json']=hashlib.sha256((root/'_owned_sql_catalog.json').read_bytes()).hexdigest()
p=root/'production_software_qualification.json';p.write_text(json.dumps({'version':'production-software-qualification.v2','baseline':'206153da27edb5353e7106ab52b6e5bcaad86627','files':files},indent=2,sort_keys=True)+'\n')
pin=hashlib.sha256(p.read_bytes()).hexdigest();p=root/'production_trial_admission.py';raw=p.read_bytes();_,old=normalize(raw,'PRODUCTION_QUALIFICATION_HASH');p.write_bytes(raw.replace(('PRODUCTION_QUALIFICATION_HASH = "'+old+'"').encode(), ('PRODUCTION_QUALIFICATION_HASH = "'+pin+'"').encode(), 1))
# Then literal, including the actual production pin, only its own literal normalized.
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.py') if p.name!='config.py'}
p=root/'text_continuations.py';raw=p.read_bytes();normalized,old=normalize(raw,'QUALIFICATION_HASH');files[p.name]=hashlib.sha256(normalized).hexdigest()
proof=json.loads((root/'text_software_qualification.json').read_text());proof.update(files=files,review_baseline='7e29ffb397d7d7560ebdf617aa345830bc34ee33',review_candidate='94e60ca3ffe25fc1fdf427f6e31f724c4b2c8dd5')
m=root/'text_software_qualification.json';m.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');pin=hashlib.sha256(m.read_bytes()).hexdigest();p.write_bytes(raw.replace(('QUALIFICATION_HASH = "'+old+'"').encode(), ('QUALIFICATION_HASH = "'+pin+'"').encode(), 1))
print(json.dumps({'production_manifest':hashlib.sha256((root/'production_software_qualification.json').read_bytes()).hexdigest(),'literal_manifest':pin,'python_files':len(files)}))
