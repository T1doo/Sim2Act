from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/tmp/sim2act-report-locks-integration-20261009');kind=sys.argv[1];assert kind in ('sqlite','pg')
freeze=json.loads((root/'byte-freeze.json').read_text())
def match():return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in freeze['files'].items())
assert match()
env={**os.environ,'LIVE':'0','SIM2ACT_LIVE_ENABLED':'false','NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules','SIM2ACT_UPGRADE_OLD_ARCHIVE':'/tmp/sim2act-late-integration-20261009/old-dag','SIM2ACT_UPGRADE_CORE_ARCHIVE':'/tmp/sim2act-late-integration-20261009/core-dag','SIM2ACT_REPORT_LOCK_OLD_ARCHIVE':'/tmp/sim2act-report-edit-locks-20261009/old-afb2','SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256':'a92d5a6aeceaa2c394c9c86041de9c2ff7f6faf1d9f646437730947cea896467'}
if kind=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/report_lock_integration?host='+str(root/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
args=['.venv/bin/pytest','-q','tests/test_report_edit_locks_ui.py','tests/test_manual_locks_ui.py','tests/test_report_edit_locks_upgrade.py','tests/test_csv_dag_upgrade.py','tests/test_report_edit_locks.py::test_report_lock_blocks_actual_original_edit_unlock_new_plan_and_readback','tests/test_report_edit_locks.py::test_report_lock_cold_store_same_key_recovery_and_superseded_history','tests/test_report_edit_locks.py::test_report_lock_two_real_connections_have_one_revision_winner','tests/test_report_edit_locks.py::test_report_lock_pg_business_crud_role_and_cold_receipt','tests/test_manual_locks.py::test_pg_minimum_crud_role_manual_lock_and_cold_receipt','--basetemp='+str(root/kind),'--junitxml='+str(root/(kind+'.xml'))]
(root/(kind+'-command.json')).write_text(json.dumps({'integrated_sha':freeze['integrated_sha'],'argv':args,'LIVE':0},indent=2)+'\n')
start=time.monotonic()
with (root/(kind+'.log')).open('w') as log:r=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
assert match()
(root/(kind+'.exit')).write_text(str(r.returncode)+'\n');(root/(kind+'-run.json')).write_text(json.dumps({'exit':r.returncode,'elapsed':time.monotonic()-start,'byte_match':True},indent=2)+'\n')
print((root/(kind+'.log')).read_text()[-12000:]);sys.exit(r.returncode)
