from pathlib import Path
import datetime,hashlib,io,json,os,shlex,subprocess,tarfile
repo=Path('/workspace/Sim2Act');dest=Path(__file__).parent;snapshot=dest/'snapshot';snapshot.mkdir()
source='2c530db7c25836f5851de057771450ff632c379d'
env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'}
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo,env=env)
tree=git('ls-tree','-rz','--full-tree',source,'--','src','tests','pyproject.toml','docs/evidence/bounded-agent-offline-20261006/independent-gold.json');expected={}
for item in tree.split(b'\0'):
 if not item:continue
 meta,path=item.split(b'\t');mode,kind,blob=meta.decode().split();assert kind=='blob'and mode in['100644','100755'],(mode,path)
 expected[path.decode()]={'git_blob_sha1':blob}
archive=git('archive',source,'src','tests','pyproject.toml','docs/evidence/bounded-agent-offline-20261006/independent-gold.json')
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:')as tar:
 for member in tar:
  path=Path(member.name);assert not path.is_absolute()and '..'not in path.parts and(member.isfile()or member.isdir()),member.name
  target=snapshot/path
  if member.isdir():target.mkdir(parents=True,exist_ok=True)
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read());target.chmod(0o444)
link=snapshot/'scripts/engineering-ci/node_modules';link.parent.mkdir(parents=True);link.symlink_to('/workspace/Sim2Act/scripts/engineering-ci/node_modules',target_is_directory=True)
(dest/'export-provenance.json').write_text(json.dumps({'source':source,'kind':'read-only git archive export; no workspace source import','export_paths':['src','tests','pyproject.toml','docs/evidence/bounded-agent-offline-20261006/independent-gold.json'],'dependency_symlink':{'path':str(link),'target':str(link.resolve())},'file_count':len(expected)},indent=2)+'\n')
def take(label):
 files={}
 for name,record in expected.items():
  data=(snapshot/name).read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert actual==record['git_blob_sha1'],name
  files[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':actual,'matches_frozen_git':True}
 out={'source':source,'snapshot_root':str(snapshot),'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'all_match_frozen_git':True,'workspace_not_used_for_execution':True}
 (dest/f'source-{label}.json').write_text(json.dumps(out,indent=2)+'\n')
 return out
before=take('before')
command=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_ordinary_csv_report.py::test_visible_prospective_csv_report','-k','workspace or scope','--basetemp='+str(dest/'data'),'--junitxml='+str(dest/'junit.xml'),'-o','cache_dir='+str(dest/'pytest-cache')]
(dest/'command.txt').write_text('cwd: '+str(snapshot)+'\nPYTHONPATH=src\nPYTHONDONTWRITEBYTECODE=1\nNODE_PATH='+env['NODE_PATH']+'\nGIT_OPTIONAL_LOCKS=0\n'+shlex.join(command)+'\n')
with(dest/'pytest.log').open('wb')as log:r=subprocess.run(command,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT)
(dest/'pytest.exit-code').write_text(str(r.returncode)+'\n');after=take('after');assert before['files']==after['files']
print(json.dumps({'returncode':r.returncode,'directory':str(dest),'snapshot_source':source,'source_files':len(expected)}),flush=True);raise SystemExit(r.returncode)
