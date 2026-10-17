from pathlib import Path
import datetime, hashlib, json, os, shlex, subprocess
root=Path('/workspace/Sim2Act')
dest=Path(__file__).parent
source='09155e6e3415acb1d53aff80248d745badd37805'
env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','PYTHONPATH':'src','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'}
def git(*args):
 return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,env=env).decode()
paths=git('ls-files','src/','tests/ordinary_run_materials.cjs','tests/test_ordinary_run_materials.py','tests/conftest.py','tests/test_literal_directory.py').splitlines()
def snapshot(label):
 head=git('rev-parse','HEAD').strip()
 files={}
 for path in paths:
  data=(root/path).read_bytes()
  frozen=subprocess.check_output(['git','-c','core.fsmonitor=false','show',f'{source}:{path}'],cwd=root,env=env)
  files[path]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'frozen_git_sha256':hashlib.sha256(frozen).hexdigest(),'matches_frozen':data==frozen}
 out={'head':head,'expected_source':source,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'all_match_frozen':all(x['matches_frozen'] for x in files.values()),'src_and_selected_tests_diff':git('diff','--name-only',source,'--',*paths),'untracked_src':git('ls-files','--others','--exclude-standard','--','src/')}
 (dest/f'source-{label}.json').write_text(json.dumps(out,indent=2)+'\n')
 assert head==source and out['all_match_frozen'] and not out['src_and_selected_tests_diff'] and not out['untracked_src'],out
 return out
snapshot('before')
command=['/workspace/sim2act-venv/bin/python','-m','pytest','tests/test_ordinary_run_materials.py','-q','-ra','--basetemp='+str(dest/'data'),'--junitxml='+str(dest/'junit.xml'),'-o','cache_dir='+str(dest/'pytest-cache')]
(dest/'command.txt').write_text('cwd: '+str(root)+'\nPYTHONPATH=src\nNODE_PATH='+env['NODE_PATH']+'\nGIT_OPTIONAL_LOCKS=0\n'+shlex.join(command)+'\n')
with (dest/'pytest.log').open('wb') as log:
 result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
(dest/'pytest.exit-code').write_text(str(result.returncode)+'\n')
snapshot('after')
print(json.dumps({'returncode':result.returncode,'directory':str(dest)}),flush=True)
raise SystemExit(result.returncode)
