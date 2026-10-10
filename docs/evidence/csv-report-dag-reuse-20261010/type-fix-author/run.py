import os,json,subprocess,time,sys,hashlib
from pathlib import Path
root=Path('/tmp/sim2act-report-dag-type-fix-20261010');db=sys.argv[1]
old=Path('/tmp/sim2act-report-dag-reuse-20261010/old-f13')
env={**os.environ,'LIVE':'0','NODE_PATH':'/tmp/sim2act-native-prerequisites-20261010/node-tools/node_modules','SIM2ACT_DAG_REUSE_OLD_ARCHIVE':'/tmp/sim2act-dag-reuse-20261010/old-67','SIM2ACT_REPORT_DAG_OLD_ARCHIVE':str(old),'SIM2ACT_REPORT_DAG_OLD_MODULE_SHA256':hashlib.sha256((old/'src/sim2act/csv_dag_instances.py').read_bytes()).hexdigest()}
if db=='pg':env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/report_type_fixture?host='+str(root/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
targets=['tests/test_csv_report_dag_instances.py::test_resigned_float_count_cannot_impersonate_integer_receipt','tests/test_csv_report_dag_instances.py::test_completed_report_flow_reexecutes_two_cold_columns_and_preserves_full_proofs','tests/test_csv_report_dag_instances.py::test_report_terminal_failure_rolls_back_the_actual_typed_append','tests/test_csv_report_dag_instances.py::test_actual_f13_upgrade_preserves_old_rows_and_requires_fresh_source','tests/test_csv_dag_instances.py::test_actual_two_nodes_two_cold_columns_instances_and_read_only_recovery','tests/test_csv_dag_instances_ui.py']
args=['.venv/bin/python','-m','pytest',*targets,'-v','--durations=10','--basetemp='+str(root/(db+'-fixtures')),'--junitxml='+str(root/(db+'.xml'))]
start=time.monotonic()
try:
 with (root/(db+'.log')).open('w') as f:p=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=210)
 code=p.returncode
except subprocess.TimeoutExpired:code=124
(root/(db+'-run.json')).write_text(json.dumps(dict(argv=args,exit=code,elapsed_seconds=time.monotonic()-start,source_sha='50b10417a99a070f6bcd614471cc00ec102b7836',LIVE=0),indent=2)+'\n');print(db,code);sys.exit(code)
