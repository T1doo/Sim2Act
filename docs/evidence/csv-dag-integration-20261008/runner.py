"""Scoped frozen-source author validation; never starts CI or any live model."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

out = Path('docs/evidence/csv-dag-integration-20261008')
name = sys.argv[1]
suite = ['tests/test_csv_dag_proof_guards.py', 'tests/test_csv_dag.py',
         'tests/test_csv_dag_boundaries.py', 'tests/test_csv_dag_ui.py',
         'tests/test_column_patch_controls.py', 'tests/test_column_patch_keys.py',
         'tests/test_column_patches.py', 'tests/test_column_patch_ui.py',
         'tests/test_delivery_graph_apps_ui.py']
suite += ['tests/test_csv_dag_upgrade.py', 'tests/test_foundation.py', 'tests/test_contract_semantics.py', 'tests/test_install_preflight.py', 'tests/test_runtime_coordination.py', 'tests/test_persistent_app_runs.py', 'tests/test_app_previews.py', 'tests/test_report_manifest_apps.py', 'tests/test_report_manifest_apps_ui.py', 'tests/test_protocol_recovery.py', 'tests/test_conditional_run_bindings.py']
files = subprocess.check_output(['git','ls-files','src','tests'],text=True).splitlines()
def hashes():
    return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
sha = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
before = hashes()
fixture = '/tmp/sim2act-dag-integration-tests-' + name
with (out/(name+'.log')).open('w') as log:
    r = subprocess.run([sys.executable,'-m','pytest','-q',*suite,'--basetemp='+fixture,
        '--junitxml='+str(out/(name+'.xml'))],stdout=log,stderr=subprocess.STDOUT,
        env={**os.environ,'LIVE':'0','NODE_PATH':'/tmp/sim2act-dag-integration-node/node_modules'})
after = hashes()
(out/(name+'-provenance.json')).write_text(json.dumps(dict(source_sha=sha,suite=suite,
    before=before,after=after,source_unchanged=before==after,returncode=r.returncode,
    fixture_root=fixture,live=0,model_mode='mock'),indent=2))
raise SystemExit(r.returncode)
