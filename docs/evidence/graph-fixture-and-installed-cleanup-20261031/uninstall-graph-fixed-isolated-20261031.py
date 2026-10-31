import hashlib,json,subprocess,sys
from pathlib import Path
repo=Path('/workspace/Sim2Act')
root=Path('/workspace/scratch/limited-text-installed-graph-fixed-20261031')
python=root/'bin/python';site=root/'lib/python3.12/site-packages'
assert root.is_dir() and not root.is_symlink()
def probe(code):return json.loads(subprocess.check_output([str(python),'-I','-B','-c',code],cwd='/workspace/scratch',text=True))
original=probe("import importlib.metadata,json; d=importlib.metadata.distribution('sim2act'); print(json.dumps({'package':str(d.locate_file('sim2act')),'metadata':str(d._path)}))")
assert Path(original['package'])==site/'sim2act'
assert Path(original['metadata']).parent==site
files={}
for directory in [Path('/workspace/scratch/installed-graph-fixed-cli-20261031/workspace'),Path('/workspace/scratch/installed-graph-fixed-live-history-20261031/workspace')]:
 for p in directory.rglob('*'):
  assert not p.is_symlink()
  if p.is_file():files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
shared={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'.venv/lib/python3.12/site-packages').glob('*.dist-info/METADATA')}
command=[str(repo/'.venv/bin/python'),'-m','pip','--python',str(python),'uninstall','--yes','sim2act']
r=subprocess.run(command,cwd='/workspace/scratch',capture_output=True,text=True,timeout=30)
Path('/workspace/scratch/graph-fixed-uninstall-20261031.log').write_text(r.stdout+r.stderr)
assert r.returncode==0
observed=probe("import importlib.util,json; print(json.dumps({'module_absent':importlib.util.find_spec('sim2act') is None}))")
assert observed['module_absent']
assert not (site/'sim2act').exists() and not (root/'bin/sim2act').exists()
assert not any(site.glob('sim2act-*.dist-info'))
assert all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in files.items())
assert all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in shared.items())
report={'candidate_source':sys.argv[1],'scope':'Uninstall only new application wheel from owned isolated scratch venv; no user data removed','command':command,'returncode':r.returncode,'installed_distribution_before':original,'module_absent_after':True,'command_entry_absent_after':True,'target_package_and_dist_info_absent_after':True,'workspace_files_unchanged':files,'shared_metadata_files_unchanged':len(shared),'shared_environment_uninstalled':False,'virtual_environment_deleted':False,'workspace_deleted':False,'real_model_requests':0}
Path('/workspace/scratch/graph-fixed-uninstall-20261031.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'returncode':r.returncode,'module_absent':True,'retained_workspace_files':len(files),'shared_metadata_unchanged':len(shared)}))
