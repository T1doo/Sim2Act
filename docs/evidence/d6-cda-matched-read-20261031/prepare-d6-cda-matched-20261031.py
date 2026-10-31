from pathlib import Path
import subprocess,tarfile,hashlib,json,shutil
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch')
old=json.loads((s/'use-manifest-baseline-c6a42c78-20261031-manifest.json').read_text());docs=[n for n in old['files'] if n.startswith('docs/')]
for label,sha in [('d6d07','d6d07d574015c02a4a86341d492ea0628c9cc2d7'),('cda0','cda0a740559cf4e1880366ed48d49ab58831b340')]:
 out=s/('matched-'+label+'-source-20261031');assert not out.exists();archive=Path(str(out)+'.tar')
 with archive.open('wb') as f:subprocess.run(['git','archive','--format=tar',sha,'src','tests','schemas','setup.py','pyproject.toml','README.md',*docs],cwd=repo,stdout=f,check=True)
 out.mkdir()
 with tarfile.open(archive) as f:f.extractall(out,filter='data')
 for p in (repo/'src/sim2act').glob('*.so'):shutil.copyfile(p,out/'src/sim2act'/p.name)
 for p in (repo/'src/sim2act').iterdir():
  if p.suffix in ('.c','.h'):assert (out/'src/sim2act'/p.name).read_bytes()==p.read_bytes()
 files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
 Path(str(out)+'-manifest.json').write_text(json.dumps(dict(source_commit=sha,export_root=str(out),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files),indent=2)+'\n')
 print(label,sha,len(files))
