"""Scoped frozen-source author validation; never starts CI or any live model."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

out = Path('docs/evidence/csv-dag-proof-fix-20261008')
name = sys.argv[1]
suite = ['tests/test_csv_dag_proof_guards.py', 'tests/test_csv_dag.py',
         'tests/test_csv_dag_boundaries.py', 'tests/test_csv_dag_ui.py',
         'tests/test_column_patch_controls.py', 'tests/test_column_patch_keys.py',
         'tests/test_column_patches.py', 'tests/test_column_patch_ui.py',
         'tests/test_delivery_graph_apps_ui.py']
files = subprocess.check_output(['git','ls-files','src','tests'],text=True).splitlines()
def hashes():
    return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
sha = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
before = hashes()
fixture = '/tmp/sim2act-proof-final-' + name
with (out/(name+'.log')).open('w') as log:
    r = subprocess.run([sys.executable,'-m','pytest','-q',*suite,'--basetemp='+fixture,
        '--junitxml='+str(out/(name+'.xml'))],stdout=log,stderr=subprocess.STDOUT,
        env={**os.environ,'LIVE':'0','NODE_PATH':'/tmp/sim2act-wiring-node/node_modules'})
after = hashes()
(out/(name+'-provenance.json')).write_text(json.dumps(dict(source_sha=sha,suite=suite,
    before=before,after=after,source_unchanged=before==after,returncode=r.returncode,
    fixture_root=fixture,live=0,model_mode='mock'),indent=2))
raise SystemExit(r.returncode)
