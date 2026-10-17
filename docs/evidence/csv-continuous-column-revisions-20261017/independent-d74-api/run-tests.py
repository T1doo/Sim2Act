import os,json,subprocess,time,pathlib,hashlib
root=pathlib.Path(__file__).parent
snapshot=root/'snapshot'
command=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','--tb=long','-p','no:cacheprovider','tests/test_csv_column_revisions.py::test_current_effective_parent_actual_check_release_adopt_and_new_result','tests/test_csv_column_revisions_negative.py','--basetemp='+str(root/'data'),'--junitxml='+str(root/'junit.xml')]
env=dict(os.environ)
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
env['PYTHONDONTWRITEBYTECODE']='1'
env['PYTHONPATH']=str(snapshot/'src')
metadata=dict(command=command,cwd=str(snapshot),git_commit='d74f2fed55b6067e5d3c34ca6e4348b92e75f48a',environment_overrides={'SIM2ACT_TEST_DATABASE_URL':'UNSET','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(snapshot/'src')},start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),start_monotonic=time.monotonic())
(root/'execution-command.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps({'started':metadata['start_utc'],'command':command}),flush=True)
with (root/'pytest.log').open('wb') as log:
 result=subprocess.run(command,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT)
metadata.update(exit_code=result.returncode,completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),elapsed_seconds=time.monotonic()-metadata['start_monotonic'])
(root/'execution-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
(root/'pytest.rc').write_text(str(result.returncode)+'\n')
print(json.dumps({'exit_code':result.returncode,'elapsed_seconds':metadata['elapsed_seconds']}),flush=True)
raise SystemExit(result.returncode)
