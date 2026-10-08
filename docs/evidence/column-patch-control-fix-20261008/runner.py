import hashlib, json, os, subprocess, sys
from pathlib import Path
root=Path('/workspace/Sim2Act')
out=root/'docs/evidence/column-patch-control-fix-20261008'
kind=sys.argv[1]
suite=['tests/test_column_patch_controls.py','tests/test_column_patch_keys.py','tests/test_column_patches.py','tests/test_column_patch_ui.py','tests/test_delivery_graph_apps_ui.py']
def hashes():
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for prefix in ('src','tests') for p in sorted((root/prefix).rglob('*')) if p.is_file() and p.suffix in ('.py','.js','.cjs','.html','.css','.csv') and '__pycache__' not in str(p)}
before=hashes()
source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
env=os.environ.copy()
env.update(SIM2ACT_MODEL_MODE='mock',SIM2ACT_LIVE_ENABLED='false',SIM2ACT_INTERN_TOKEN='',INTERN_API_TOKEN='',NODE_PATH='/tmp/sim2act-dag-node/node_modules')
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
if kind=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/postgres?host=/tmp/sim2act-control-pg/socket'
with (out/(kind+'.log')).open('w') as log:
    rc=subprocess.run([str(root/'.venv/bin/python'),'-m','pytest','-q',*suite,'--basetemp=/tmp/sim2act-control-final-'+kind,'--junitxml='+str(out/(kind+'.xml'))],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
after=hashes()
(out/(kind+'-provenance.json')).write_text(json.dumps(dict(source_sha=source,suite=suite,returncode=rc,source_unchanged=before==after,before=before,after=after,live=0),indent=2))
print(json.dumps(dict(kind=kind,source_sha=source,returncode=rc,source_unchanged=before==after)))
print((out/(kind+'.log')).read_text()[-2000:])
sys.exit(rc or (0 if before==after else 1))
