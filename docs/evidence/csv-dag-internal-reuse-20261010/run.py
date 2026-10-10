from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/tmp/sim2act-dag-reuse-20261010');kind=sys.argv[1];assert kind in ('sqlite','pg')
freeze=json.loads((root/'source-freeze.json').read_text())
def match():return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in freeze['files'].items())
assert match()
env={**os.environ,'LIVE':'0','SIM2ACT_LIVE_ENABLED':'false','NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules','SIM2ACT_UPGRADE_OLD_ARCHIVE':'/tmp/sim2act-late-integration-20261009/old-dag','SIM2ACT_UPGRADE_CORE_ARCHIVE':'/tmp/sim2act-late-integration-20261009/core-dag','SIM2ACT_REPORT_LOCK_OLD_ARCHIVE':'/tmp/sim2act-report-edit-locks-20261009/old-afb2','SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256':'a92d5a6aeceaa2c394c9c86041de9c2ff7f6faf1d9f646437730947cea896467','SIM2ACT_DAG_REUSE_OLD_ARCHIVE':str(root/'old-67')}
if kind=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/dag_reuse_fixture?host='+str(root/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
args=['.venv/bin/pytest','-q','tests/test_csv_dag_instances.py','tests/test_csv_dag_instances_ui.py','tests/test_csv_dag.py','tests/test_csv_composition_ui.py','tests/test_csv_composition.py::test_four_actual_nodes_two_new_outputs_original_objects_unchanged','tests/test_application_use.py','tests/test_internal_lifecycle.py::test_completed_task_internal_release_instances_fresh_runs_cold_data_no_preview_copy','tests/test_internal_lifecycle.py::test_current_grant_revocation_or_expiry_blocks_new_run_and_read','tests/test_internal_lifecycle.py::test_instance_lineage_copy_and_request_key_fingerprint_reject','tests/test_csv_dag_upgrade.py','tests/test_report_edit_locks_upgrade.py','tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback[same-checks]','--basetemp='+str(root/kind),'--junitxml='+str(root/(kind+'.xml'))]
(root/(kind+'-command.json')).write_text(json.dumps({'source_sha':freeze['source_sha'],'argv':args,'LIVE':0},indent=2)+'\n')
start=time.monotonic()
with (root/(kind+'.log')).open('w') as log:p=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
unchanged=match();(root/(kind+'-run.json')).write_text(json.dumps({'exit':p.returncode,'wall_seconds':time.monotonic()-start,'source_files':len(freeze['files']),'byte_match':unchanged},indent=2)+'\n')
print((root/(kind+'.log')).read_text()[-3500:]);assert unchanged;sys.exit(p.returncode)
