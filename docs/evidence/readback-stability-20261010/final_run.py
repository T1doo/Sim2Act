from pathlib import Path
import hashlib,json,os,subprocess,sys,time
r=Path('/tmp/sim2act-read-stability-20261010');kind=sys.argv[1];assert kind in ('sqlite','pg')
f=json.loads((r/'source-freeze.json').read_text())
def match():return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in f['files'].items())
assert match()
env={**os.environ,'LIVE':'0','SIM2ACT_LIVE_ENABLED':'false','NODE_PATH':'/tmp/sim2act-late-integration-20261009/node/node_modules',
 'PYTHONPATH':str(r),'STABILITY_PROFILE_OUT':str(r/(kind+'-profile')),'STABILITY_SOURCE_SHA':f['source_sha'],
 'SIM2ACT_UPGRADE_OLD_ARCHIVE':'/tmp/sim2act-late-integration-20261009/old-dag','SIM2ACT_UPGRADE_CORE_ARCHIVE':'/tmp/sim2act-late-integration-20261009/core-dag',
 'SIM2ACT_REPORT_LOCK_OLD_ARCHIVE':'/tmp/sim2act-report-edit-locks-20261009/old-afb2','SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256':'a92d5a6aeceaa2c394c9c86041de9c2ff7f6faf1d9f646437730947cea896467',
 'SIM2ACT_DAG_REUSE_OLD_ARCHIVE':'/tmp/sim2act-dag-reuse-20261010/old-67'}
if kind=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/read_stability_fixture?host='+str(r/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
nodes=['tests/test_report_presentations.py','tests/test_report_history_scoped_readback.py','tests/test_report_presentation_late_ui.py',
 'tests/test_report_history_feedback_ui.py::test_damaged_history_current_feedback_and_exact_recovery[checks-item-None]',
 'tests/test_report_history_feedback_ui.py::test_damaged_history_current_feedback_and_exact_recovery[definition-envelope-None]',
 'tests/test_report_edit_locks.py::test_report_lock_blocks_actual_original_edit_unlock_new_plan_and_readback',
 'tests/test_report_edit_locks.py::test_report_lock_cold_store_same_key_recovery_and_superseded_history',
 'tests/test_report_edit_locks.py::test_report_lock_pg_business_crud_role_and_cold_receipt',
 'tests/test_report_edit_locks_upgrade.py','tests/test_csv_dag_instances.py::test_actual_previous_dev_source_upgrade_preserves_old_proofs_and_requires_fresh_source',
 'tests/test_csv_dag_instances.py::test_actual_two_nodes_two_cold_columns_instances_and_read_only_recovery',
 'tests/test_csv_dag_instances.py::test_atomic_final_transaction_rolls_back_typed_append_on_terminal_write_failure',
 'tests/test_csv_dag_instances.py::test_joint_pair_marker_and_join_deletion_cannot_hide_actual_accepted_event',
 'tests/test_application_use.py','tests/test_resources_project_lock.py::test_pg_resources_graph_share_project_first_lock',
 'tests/test_csv_dag_upgrade.py','tests/test_report_manifest_apps_ui.py']
args=['.venv/bin/pytest','-q','-p','profile_plugin',*nodes,'--basetemp='+str(r/kind),'--junitxml='+str(r/(kind+'.xml'))]
(r/(kind+'-command.json')).write_text(json.dumps(dict(source_sha=f['source_sha'],argv=args,LIVE=0,raw_timeout_or_observer_changes=False),indent=2)+'\n')
start=time.monotonic()
with (r/(kind+'.log')).open('w') as log:p=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
unchanged=match();(r/(kind+'-run.json')).write_text(json.dumps(dict(source_sha=f['source_sha'],exit=p.returncode,wall_seconds=time.monotonic()-start,source_files=len(f['files']),byte_match=unchanged),indent=2)+'\n')
print((r/(kind+'.log')).read_text()[-4000:]);assert unchanged;sys.exit(p.returncode)
