"""One owned isolated runtime, public original PyPI wheels, no PG/model/network provisioning."""
import hashlib,json,os,subprocess,sys,zipfile
from email.parser import BytesParser
from pathlib import Path
from sim2act.process_env import system_environment
from sim2act.desktop_protocol import ordinary
root=ordinary('/workspace/scratch/sim2act-pg-locked-runtime-20261101')
root.mkdir(mode=0o700,exist_ok=False)
repo=Path('/workspace/Sim2Act');private_log=root/'build.private.log'
log=private_log.open('x');os.chmod(private_log,0o600)
def run(args,timeout):
 value=subprocess.run(args,cwd=repo,env=system_environment(),stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 if value.returncode:raise SystemExit('ISOLATED_RUNTIME_BUILD_FAILED_PRIVATE_LOG_PRESERVED')
run([sys.executable,'-m','venv',str(root/'venv')],60)
python=root/'venv/bin/python';wheels=root/'wheels';wheels.mkdir()
run([str(python),'-m','pip','--isolated','--disable-pip-version-check','download','--no-cache-dir','--only-binary=:all:',
     '--no-deps','--index-url','https://pypi.org/simple','-r',str(repo/'requirements.lock'),'--dest',str(wheels)],180)
expected={}
for line in (repo/'requirements.lock').read_text().splitlines():
 if line and not line.startswith('#'):
  name,version=line.split('==');expected[name.lower().replace('_','-')]=version
records={}
for file in wheels.iterdir():
 assert file.suffix=='.whl'
 with zipfile.ZipFile(file) as z:
  paths=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')];assert len(paths)==1
  m=BytesParser().parsebytes(z.read(paths[0]));name=m['Name'].lower().replace('_','-');version=m['Version']
  assert expected.get(name)==version and name not in records
 records[name]=dict(filename=file.name,version=version,size=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),source='original public https://pypi.org/simple; pip TLS unchanged')
assert set(expected)==set(records)
run([str(python),'-m','pip','--isolated','--disable-pip-version-check','install','--no-index','--no-deps',
     '--find-links',str(wheels),'-r',str(repo/'requirements.lock')],120)
site=next((root/'venv/lib').glob('python3.12/site-packages'));pth=site/'sim2act-reviewed-source.pth'
pth.write_text(str(repo/'src')+'\n')
run([str(python),'-m','pip','check'],30)
log.close()
(root/'runtime-manifest.json').write_text(json.dumps(dict(status='INSTALLED_LOCKED_RUNTIME_NOT_PG_ACCEPTANCE',source_sha='57122dc311742653ba3ab2902d188fdb33b1dcd5',python=str(python),lock_sha256=hashlib.sha256((repo/'requirements.lock').read_bytes()).hexdigest(),source_binding=str(pth),source_directory=str(repo/'src'),artifacts=records,original_venv_untouched=True,new_credentials=0,new_pg_resources=0,actual_model_calls=0),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='COMPLETE',python=str(python),locked_packages=len(records),manifest=str(root/'runtime-manifest.json'))))
