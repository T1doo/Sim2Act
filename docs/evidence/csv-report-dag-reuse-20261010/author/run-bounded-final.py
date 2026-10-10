import os,json,subprocess,time,sys
from pathlib import Path
root=Path('/tmp/sim2act-report-dag-reuse-20261010'); db=sys.argv[1]
env={**os.environ,'LIVE':'0','NODE_PATH':'/tmp/sim2act-native-prerequisites-20261010/node-tools/node_modules','SIM2ACT_DAG_REUSE_OLD_ARCHIVE':'/tmp/sim2act-dag-reuse-20261010/old-67','SIM2ACT_REPORT_DAG_OLD_ARCHIVE':str(root/'old-f13'),'SIM2ACT_REPORT_DAG_OLD_MODULE_SHA256':__import__('hashlib').sha256((root/'old-f13/src/sim2act/csv_dag_instances.py').read_bytes()).hexdigest()}
if db.startswith('pg'):env['SIM2ACT_TEST_DATABASE_URL']='postgresql+psycopg://postgres@/report_dag_fixture?host='+str(root/'pg-socket')
else:env.pop('SIM2ACT_TEST_DATABASE_URL',None)
files=['tests/test_csv_dag_instances.py','tests/test_csv_report_dag_instances.py','tests/test_csv_dag_instances_ui.py','tests/test_csv_composition.py','tests/test_csv_composition_ui.py','tests/test_report_presentation_late_ui.py']
args=['.venv/bin/python','-m','pytest',*files,'-v','--durations=15','--basetemp='+str(root/(db+'-fixtures')),'--junitxml='+str(root/(db+'.xml'))]
start=time.monotonic()
with (root/(db+'.log')).open('w') as f:p=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=700)
(root/(db+'-run.json')).write_text(json.dumps(dict(argv=args,exit=p.returncode,elapsed_seconds=time.monotonic()-start,source_sha='5588a94faeb90abb2052a8ae5327810b8d27c287',LIVE=0),indent=2)+'\n');print(db,p.returncode);sys.exit(p.returncode)
