import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path('/workspace/Sim2Act')
out = root / 'docs/evidence/column-binding-patch-20261008'
suite = [
    'test_column_patches.py', 'test_column_patch_ui.py', 'test_delivery_graph.py',
    'test_delivery_graph_apps.py', 'test_delivery_graph_apps_ui.py',
    'test_delivery_graph_receipt_types.py', 'test_delivery_graph_source_version_types.py',
    'test_delivery_graph_adapter_contract.py', 'test_delivery_graph_service_contract.py',
    'test_app_previews.py', 'test_preview_extraction.py', 'test_registered_run_extraction.py',
    'test_internal_lifecycle.py', 'test_application_use.py', 'test_report_manifest_apps.py',
    'test_report_manifest_apps_ui.py', 'test_contract_semantics.py',
]
kind = sys.argv[1]
paths = ['tests/' + name for name in suite]
source = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
changed = subprocess.check_output(['git','diff','--name-only','122b2e6f',source], cwd=root,text=True).splitlines()
def manifest():
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in changed
            if name.startswith(('src/','tests/'))}
before = manifest()
env = os.environ.copy()
env.update(SIM2ACT_MODEL_MODE='mock', SIM2ACT_LIVE_ENABLED='false', SIM2ACT_INTERN_TOKEN='',
           INTERN_API_TOKEN='', NODE_PATH='/tmp/sim2act-column-node/node_modules')
env.pop('SIM2ACT_TEST_DATABASE_URL', None)
if kind == 'pg':
    env['SIM2ACT_TEST_DATABASE_URL'] = 'postgresql+psycopg://postgres@/postgres?host=/tmp/sim2act-column-pg/socket'
args = [str(root/'.venv/bin/python'), '-m','pytest','-q', *paths,
        '--basetemp=/tmp/sim2act-column-final-'+kind,
        '--junitxml='+str(out/(kind+'-junit.xml'))]
with (out/(kind+'-final.log')).open('w') as log:
    result = subprocess.run(args, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
after = manifest()
(out/(kind+'-provenance.json')).write_text(json.dumps(dict(
    source_sha=source, suite=paths, returncode=result.returncode, before=before, after=after,
    source_unchanged=before==after, model_mode='mock', live=0,
    fixture_root='/tmp/sim2act-column-final-'+kind),indent=2))
print(json.dumps(dict(kind=kind,returncode=result.returncode,source_sha=source,source_unchanged=before==after)))
print((out/(kind+'-final.log')).read_text()[-5000:])
sys.exit(result.returncode or (0 if before == after else 1))
