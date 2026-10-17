from pathlib import Path
import datetime,hashlib,json,os,shlex,subprocess
root=Path('/workspace/Sim2Act');dest=Path(__file__).parent;source='aed84dfc36eb6e810760331bd72b5f9853b981d5'
env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'}
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,env=env)
expected={}
for item in git('ls-tree','-rz','--full-tree',source,'--','src','tests','pyproject.toml').split(b'\0'):
 if item:
  meta,path=item.split(b'\t');expected[path.decode()]=meta.decode().split()[2]
def take(label):
 files={}
 for name,blob in expected.items():
  data=(root/name).read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert actual==blob,name
  files[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':blob,'matches_frozen_git':True}
 out={'head':git('rev-parse','HEAD').decode().strip(),'source':source,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'all_match_frozen_git':True,'diff':git('diff','--name-only',source,'--','src','tests','pyproject.toml').decode(),'untracked_src':git('ls-files','--others','--exclude-standard','--','src').decode()}
 (dest/f'source-{label}.json').write_text(json.dumps(out,indent=2)+'\n');assert out['head']==source and not out['diff']and not out['untracked_src'];return out
before=take('before')
command=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_ordinary_csv_report.py::test_visible_prospective_csv_report','tests/test_ordinary_run_results.py::test_ordinary_goal_results_actual_tools_and_page[workspace-return]','--basetemp='+str(dest/'data'),'--junitxml='+str(dest/'junit.xml'),'-o','cache_dir='+str(dest/'pytest-cache')]
(dest/'command.txt').write_text('cwd: '+str(root)+'\nPYTHONPATH=src\nPYTHONDONTWRITEBYTECODE=1\nNODE_PATH='+env['NODE_PATH']+'\nGIT_OPTIONAL_LOCKS=0\n'+shlex.join(command)+'\n')
with(dest/'pytest.log').open('wb')as log:r=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
(dest/'pytest.exit-code').write_text(str(r.returncode)+'\n');after=take('after');assert before['files']==after['files']
print(json.dumps({'returncode':r.returncode,'directory':str(dest),'source':source,'source_files':len(expected)}),flush=True);raise SystemExit(r.returncode)
