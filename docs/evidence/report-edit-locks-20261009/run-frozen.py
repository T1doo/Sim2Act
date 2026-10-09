import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/tmp/sim2act-report-edit-locks-20261009')
kind=sys.argv[1]
assert kind in ('sqlite','pg')
freeze=json.loads((root/'source-freeze-final.json').read_text())
def matching():
    return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in freeze['files'].items())
assert matching()
env={**os.environ,'LIVE':'0','SIM2ACT_LIVE_ENABLED':'false','NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules','SIM2ACT_UPGRADE_OLD_ARCHIVE':'/tmp/sim2act-late-integration-20261009/old-dag','SIM2ACT_UPGRADE_CORE_ARCHIVE':'/tmp/sim2act-late-integration-20261009/core-dag','SIM2ACT_REPORT_LOCK_OLD_ARCHIVE':str(root/'old-afb2'),'SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256':'a92d5a6aeceaa2c394c9c86041de9c2ff7f6faf1d9f646437730947cea896467'}
if kind=='pg':
    env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/report_locks_fixture?host='+str(root/'pg-socket')
else:
    env.pop('SIM2ACT_TEST_DATABASE_URL',None)
args=['.venv/bin/pytest','-q','tests/test_report_edit_locks.py','tests/test_report_edit_locks_ui.py','tests/test_report_edit_locks_upgrade.py','tests/test_manual_locks.py','tests/test_manual_locks_ui.py','tests/test_report_presentations.py','tests/test_report_presentation_ui.py','tests/test_report_manifest_apps_ui.py','tests/test_csv_dag_upgrade.py']
args += ['tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback['+p+']' for p in ('same-definition','same-checks','other_app-checks','identity-checks')]
args += ['--basetemp='+str(root/(kind+'-final')),'--junitxml='+str(root/(kind+'-final.xml'))]
(root/(kind+'-final-command.json')).write_text(json.dumps({'source_sha':freeze['source_sha'],'argv':args,'LIVE':0,'old_report_source':'afb2f1f3813fc3a4744923f31bbcb4666b88cccd','transport':'synthetic fixtures and actual loopback HTTP','database':kind},indent=2)+'\n')
start=time.monotonic()
with (root/(kind+'-final.log')).open('w') as log:
    result=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
assert matching(), 'Source bytes changed during frozen test'
(root/(kind+'-final.exit')).write_text(str(result.returncode)+'\n')
(root/(kind+'-final-run.json')).write_text(json.dumps({'source_sha':freeze['source_sha'],'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'source_bytes_unchanged':True},indent=2)+'\n')
print((root/(kind+'-final.log')).read_text()[-12000:])
sys.exit(result.returncode)
