from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/tmp/sim2act-project-checks-20261009');kind=sys.argv[1];assert kind in ('sqlite','pg')
freeze=json.loads((root/'byte-freeze.json').read_text())
def match():return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in freeze['files'].items())
assert match()
env={**os.environ,'LIVE':'0','SIM2ACT_LIVE_ENABLED':'false','SIM2ACT_PROJECT_CHECK_OLD_ARCHIVE':str(root/'old-5fed'),'SIM2ACT_PROJECT_CHECK_OLD_API_SHA256':'7223c25689b1590f008f8f32d094a6c11c39576272207a521b17797aa2af0bdf','NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules','SIM2ACT_UPGRADE_OLD_ARCHIVE':'/tmp/sim2act-late-integration-20261009/old-dag','SIM2ACT_UPGRADE_CORE_ARCHIVE':'/tmp/sim2act-late-integration-20261009/core-dag','SIM2ACT_REPORT_LOCK_OLD_ARCHIVE':'/tmp/sim2act-report-edit-locks-20261009/old-afb2','SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256':'a92d5a6aeceaa2c394c9c86041de9c2ff7f6faf1d9f646437730947cea896467'}
if kind=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/project_checks_fixture?host='+str(root/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
args=['.venv/bin/pytest', '-q', 'tests/test_project_revalidation.py', 'tests/test_project_revalidation_ui.py', 'tests/test_project_revalidation_upgrade.py', 'tests/test_delivery_graph_apps.py::test_csv_real_anchor_restart_idempotency_and_pending_scope_jobs', 'tests/test_delivery_graph_apps.py::test_real_report_origin_two_sources_project_pending_jobs_and_unsupported_omission', 'tests/test_delivery_graph_apps.py::test_project_missing_peer_anchor_is_explicit_partial_not_candidate_only_job', 'tests/test_report_presentations.py::test_new_immutable_presentation_and_actual_archived_readback_preserve_canonical', 'tests/test_manual_locks_ui.py', 'tests/test_report_edit_locks_ui.py', 'tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback[lost_response-checks]', 'tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback[lost_response-definition]', 'tests/test_report_edit_locks_upgrade.py', 'tests/test_csv_dag_upgrade.py']+['--basetemp='+str(root/kind),'--junitxml='+str(root/(kind+'.xml'))]
(root/(kind+'-command.json')).write_text(json.dumps({'source_sha':freeze['source_sha'],'argv':args,'LIVE':0},indent=2)+'\n')
start=time.monotonic()
with (root/(kind+'.log')).open('w') as log:r=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
assert match()
(root/(kind+'.exit')).write_text(str(r.returncode)+'\n');(root/(kind+'-run.json')).write_text(json.dumps({'exit':r.returncode,'elapsed':time.monotonic()-start,'byte_match':True},indent=2)+'\n')
print((root/(kind+'.log')).read_text()[-12000:]);sys.exit(r.returncode)
