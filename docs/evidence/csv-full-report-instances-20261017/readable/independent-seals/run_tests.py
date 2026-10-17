import datetime, json, os, pathlib, subprocess, time
out=pathlib.Path('/tmp/f2-csv-full-report-d2bacd5c-seals-independent')
snapshot=out/'snapshot'
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_csv_full_report_instance_seals.py','--basetemp='+str(out/'pytest'),'--junitxml='+str(out/'junit.xml'),'-o','cache_dir='+str(out/'pytest-cache')]
env=os.environ.copy()
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
env.update(PYTHONPATH=str(snapshot/'src')+':'+str(snapshot/'tests'),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
start=time.monotonic()
receipt={'source_sha':'d2bacd5ccab8ac848956aa637771848ca58404a5','cwd':str(snapshot),'argv':cmd,'env_overrides':{k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD']},'SIM2ACT_TEST_DATABASE_URL':'removed','start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/'execution-start.json').write_text(json.dumps(receipt,indent=2)+'\n')
with (out/'pytest.log').open('wb') as log:
 proc=subprocess.Popen(cmd,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT)
 receipt['pid']=proc.pid
 (out/'execution-start.json').write_text(json.dumps(receipt,indent=2)+'\n')
 rc=proc.wait()
receipt.update(returncode=rc,elapsed_seconds=time.monotonic()-start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(out/'execution-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(rc)
