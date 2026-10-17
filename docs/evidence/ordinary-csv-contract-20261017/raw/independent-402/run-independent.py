from pathlib import Path
import datetime,hashlib,json,os,shlex,subprocess
root=Path('/workspace/Sim2Act');dest=Path(__file__).parent;source='402f3eb5f80be73ddc57d4bb6123fdd6157726e0'
env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'}
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,env=env).decode()
related=['tests/test_ordinary_csv_report.py','tests/ordinary_csv_report.cjs','tests/test_ordinary_run_results.py','tests/ordinary_run_results.cjs','tests/test_fixed_goal_acceptance.py','tests/conftest.py','tests/test_literal_directory.py','tests/test_natural_activation_flow.py','tests/test_natural_goal_planning.py','tests/test_natural_receipt_candidate.py']
paths=git('ls-files','src/',*related).splitlines()
def snapshot(label):
 files={}
 for path in paths:
  data=(root/path).read_bytes();frozen=subprocess.check_output(['git','-c','core.fsmonitor=false','show',f'{source}:{path}'],cwd=root,env=env)
  files[path]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'frozen_git_sha256':hashlib.sha256(frozen).hexdigest(),'matches_frozen':data==frozen}
 out={'head':git('rev-parse','HEAD').strip(),'expected_source':source,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'all_match_frozen':all(x['matches_frozen']for x in files.values()),'src_and_selected_tests_diff':git('diff','--name-only',source,'--',*paths),'untracked_src':git('ls-files','--others','--exclude-standard','--','src/')}
 (dest/f'source-{label}.json').write_text(json.dumps(out,indent=2)+'\n')
 assert out['head']==source and out['all_match_frozen']and not out['src_and_selected_tests_diff']and not out['untracked_src'],out
snapshot('before')
previous='599052cbadae21b4a7ba8738fb889ea970c11e84'
changed=git('diff','--name-only',previous,source).splitlines()
assert changed==['src/sim2act/web/ordinary-csv.js','tests/ordinary_csv_report.cjs'],changed
(dest/'source-delta-from-599.json').write_text(json.dumps({'previous_source':previous,'source':source,'all_tracked_changed_paths':changed,'all_other_tracked_files_byte_identical_between_commits':True,'diff':git('diff',previous,source)},indent=2)+'\n')
command=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_ordinary_csv_report.py::test_visible_prospective_csv_report','--basetemp='+str(dest/'data'),'--junitxml='+str(dest/'junit.xml'),'-o','cache_dir='+str(dest/'pytest-cache')]
(dest/'command.txt').write_text('cwd: '+str(root)+'\nPYTHONPATH=src\nNODE_PATH='+env['NODE_PATH']+'\nPYTHONDONTWRITEBYTECODE=1\nGIT_OPTIONAL_LOCKS=0\n'+shlex.join(command)+'\n')
with(dest/'pytest.log').open('wb')as log:result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
(dest/'pytest.exit-code').write_text(str(result.returncode)+'\n');snapshot('after')
print(json.dumps({'returncode':result.returncode,'directory':str(dest)}),flush=True);raise SystemExit(result.returncode)
