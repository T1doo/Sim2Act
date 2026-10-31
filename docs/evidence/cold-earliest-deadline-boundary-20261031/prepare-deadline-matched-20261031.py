from pathlib import Path
import subprocess,tarfile,hashlib,json,shutil
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch')
old=json.loads((s/'use-manifest-baseline-c6a42c78-20261031-manifest.json').read_text());docs=[n for n in old['files'] if n.startswith('docs/')]
for label,sha in [('baseline','2d41ad38b84630cb817d87374122bce31e357d0d'),('candidate','2ad3227621b48793a4d03747463b33207139147e')]:
 out=s/('deadline-matched-'+label+'-20261031');assert not out.exists();archive=Path(str(out)+'.tar')
 with archive.open('wb') as f:subprocess.run(['git','archive','--format=tar',sha,'src','tests','schemas','setup.py','pyproject.toml','README.md',*docs],cwd=repo,stdout=f,check=True)
 out.mkdir()
 with tarfile.open(archive) as f:f.extractall(out,filter='data')
 for p in (repo/'src/sim2act').glob('*.so'):shutil.copyfile(p,out/'src/sim2act'/p.name)
 for p in (repo/'src/sim2act').iterdir():
  if p.suffix in ('.c','.h'):assert (out/'src/sim2act'/p.name).read_bytes()==p.read_bytes()
 probe='import importlib,hashlib,json;from pathlib import Path; d={}; inputs='+repr({'_raw_snapshot':['_raw_snapshot.c'],'_cold_graph_structure':['_cold_graph_structure.c'],'_cold_typed_cohort':['_cold_typed_cohort.c','_cold_typed_native_impl.c','_raw_snapshot.c','_cold_cohort_backend.py'],'_cold_source_owned_impl':['_cold_source_owned_impl.c','_cold_source_live_match.h','_cold_source_code.h','_cold_source_view.h','_cold_source_shape.h']})+'\nfor n,fs in inputs.items():\n m=importlib.import_module("sim2act."+n);p=Path(m.__file__);assert str(p).startswith('+repr(str(out/'src/sim2act')+'/')+');assert m.SOURCE_SHA256==hashlib.sha256(b"".join((p.parent/f).read_bytes() for f in fs)).hexdigest();d[n]={"path":str(p),"binary_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"source_sha256":m.SOURCE_SHA256}\nprint(json.dumps(d))'
 import os
 env={**os.environ,'PYTHONPATH':str(out/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
 native=json.loads(subprocess.check_output([str(repo/'.venv/bin/python'),'-B','-c',probe],cwd=out,env=env,text=True))
 files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
 Path(str(out)+'-manifest.json').write_text(json.dumps(dict(source_commit=sha,export_root=str(out),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files,native=native),indent=2)+'\n')
 print(label,sha,len(files))
