import gzip,hashlib,json,os,platform,subprocess,zipfile
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/workspace/scratch/limited-text-candidate-6424cc040bc8-cc-20261031')
m=json.loads((out/'candidate-manifest.json').read_text());assert m['source_commit']=='6424cc040bc8da7fd7f1c86130e30b0f95598594'
p=next(out.glob('*.zip'));wheel=next(out.glob('*.whl'));installed=Path('/workspace/scratch/limited-text-installed-6424cc04-20261031/lib/python3.12/site-packages')
secrets=[os.environ[n].encode() for n in ['INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN'] if os.environ.get(n)]
with zipfile.ZipFile(p) as z:
 expected={'Sim2Act-local-candidate/'+n for n in m['files']}|{'Sim2Act-local-candidate/candidate-manifest.json'}
 assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==expected
 for name,r in m['files'].items():
  raw=z.read('Sim2Act-local-candidate/'+name);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
  assert all(secret not in raw for secret in secrets)
  assert not name.endswith(('.db','.sqlite','.env','.pyc')) and '/.git/' not in name
 assert z.read('Sim2Act-local-candidate/wheels/'+wheel.name)==wheel.read_bytes()
with zipfile.ZipFile(wheel) as z:
 for n in z.namelist():assert all(secret not in z.read(n) for secret in secrets)
 for name,r in m['wheel_profile']['native_artifacts'].items():
  assert hashlib.sha256((installed/name).read_bytes()).hexdigest()==r['sha256']
imports=json.loads(Path('/workspace/scratch/limited-text-installed-6424cc04-imports-20261031.json').read_text())
assert '/workspace/Sim2Act/src' not in imports['sys_path']
files={'_raw_snapshot':['_raw_snapshot.c'],'_cold_graph_structure':['_cold_graph_structure.c'],'_cold_typed_cohort':['_cold_typed_cohort.c','_cold_typed_native_impl.c','_raw_snapshot.c','_cold_cohort_backend.py'],'_cold_source_owned_impl':['_cold_source_owned_impl.c','_cold_source_live_match.h','_cold_source_code.h','_cold_source_view.h','_cold_source_shape.h']}
for name,paths in files.items():
 assert imports['native'][name]['file'].startswith(str(installed)+'/sim2act/')
 assert imports['native'][name]['source']==hashlib.sha256(b''.join((installed/'sim2act'/n).read_bytes() for n in paths)).hexdigest()
result={'candidate_source':m['source_commit'],'application_version':'0.1.0','archive_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'archive_bytes':p.stat().st_size,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'wheel_tags':m['wheel_profile']['tags'],'strict_archive_inventory_count':len(expected),'native_modules_imported_from_new_install':imports['native'],'all_embedded_source_hashes_match':True,'no_original_src_on_sys_path':True,'dependency_scope':'Existing pinned runtime packages reused; fresh isolated wheel application, no dependency download test','configured_secret_matches':0,'private_data_or_environment_files_packaged':False,'default_model_enabled':m['default_model_enabled'],'opt_in_capabilities':m['opt_in_capabilities'],'platform':platform.platform(),'glibc':platform.libc_ver(),'windows_build_or_execution':False,'model_requests_during_package_audit':0}
(out/'package-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['candidate_source','archive_bytes','archive_sha256','wheel_sha256','all_embedded_source_hashes_match','configured_secret_matches']}))
