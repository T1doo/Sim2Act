import hashlib,json,os,subprocess,sys
from pathlib import Path
out=Path('docs/evidence/csv-foundation-integration-20261008');out.mkdir(parents=True,exist_ok=True)
suite=['tests/test_column_patch_controls.py','tests/test_column_patch_keys.py','tests/test_column_patches.py','tests/test_column_patch_ui.py','tests/test_delivery_graph_apps_ui.py']
name=sys.argv[1];fixture='/tmp/sim2act-csv-integration-'+name
files=subprocess.check_output(['git','ls-files','src','tests'],text=True).splitlines()
def hashes():return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
before=hashes();sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
with (out/(name+'.log')).open('w') as log:
 r=subprocess.run([sys.executable,'-m','pytest','-q',*suite,'--basetemp='+fixture,'--junitxml='+str(out/(name+'.xml'))],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'LIVE':'0','NODE_PATH':'/tmp/sim2act-dag-node/node_modules'})
after=hashes();(out/(name+'-provenance.json')).write_text(json.dumps(dict(source_sha=sha,suite=suite,returncode=r.returncode,before=before,after=after,source_unchanged=before==after,live=0,model_mode='mock',fixture_root=fixture),indent=2));raise SystemExit(r.returncode)
