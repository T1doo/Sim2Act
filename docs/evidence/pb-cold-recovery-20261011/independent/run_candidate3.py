from pathlib import Path
import datetime,json,os,subprocess,sys,time
root=Path('/workspace/Sim2Act');out=Path('/tmp/pb-cold-recovery-review-20261011');kind=sys.argv[1]
selected={'new':['tests/test_registered_text_recovery.py','tests/test_registered_text_recovery_ui.py'],'existing':['tests/test_registered_text_extraction.py','tests/test_registered_text_ui.py']}[kind]
prefix='candidate3-'+kind
cmd=[str(root/'.venv/bin/python'),'-m','pytest','-q',*selected,'--basetemp',str(out/(prefix+'-db')),'--junitxml',str(out/(prefix+'.xml'))]
env={**os.environ,'PYTHONPATH':'src:tests','NODE_PATH':'/workspace/node-tools/node_modules','SIM2ACT_PB_EVIDENCE_DIR':str(out/'candidate3-existing-pages'),'SIM2ACT_COLD_EVIDENCE_DIR':str(out/'candidate3-cold-pages')};env.pop('SIM2ACT_TEST_DATABASE_URL',None)
assert not (out/(prefix+'.log')).exists()
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out/(prefix+'.log')).open('w') as log:
 p=subprocess.Popen(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
 status={'status':'RUNNING','pid':p.pid,'command':cmd,'started_utc':utc,'suite':kind};(out/(prefix+'-process.json')).write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status),flush=True);code=p.wait()
status.update(status='COMPLETED',exit_code=code,elapsed_seconds=round(time.monotonic()-start,2),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(out/(prefix+'-process.json')).write_text(json.dumps(status,indent=2)+'\n');(out/(prefix+'-result.json')).write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status),flush=True);print((out/(prefix+'.log')).read_text()[-8000:],flush=True);raise SystemExit(code)
