import collections,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
B=Path('/workspace/production-admission-evidence-20261015');D=Path('/workspace/Sim2Act-pa-provider/docs/evidence/production-admission-contract-20261015');O=Path('/workspace/production-admission-archive-review-20261015')
def h(p):
 z=hashlib.sha256()
 with p.open('rb') as f:
  for q in iter(lambda:f.read(1024*1024),b''):z.update(q)
 return z.hexdigest()
a=json.loads((D/'ARCHIVES.json').read_text());assert len(a)==16
names={'author','pb-author','regression','review','cold-probe','integration','cancel-diagnostic','route-before','route-before2','route-fixed','route-family-fixed','peer-lock-diagnostic','peer-lock-diagnostic2','route-local-fixed','budget-cleanup-probe','pb-heartbeat-diagnostic'};assert set(a)==names
results={};allman={};excluded={'__pycache__','.pytest_cache','mypy-cache'}
for name,receipt in a.items():
 root=B/name;man=json.loads((D/(name+'-MANIFEST.json')).read_text());target=D/receipt['file'];assert target.name==name+'-evidence.tar.gz' and target.stat().st_size==receipt['bytes'] and h(target)==receipt['sha256']
 expected={};skip=collections.Counter()
 for p in root.rglob('*'):
  rel=p.relative_to(root)
  if excluded.intersection(rel.parts):skip['declared_cache']+=1;continue
  if p.is_symlink():skip['symlink']+=1;continue
  if not p.is_file():continue
  assert not any(x.is_symlink() for x in p.parents if x!=root.parent)
  if name=='integration' and rel.as_posix()=='PACKAGE_RESULT.json':skip['self_result']+=1;continue
  expected[rel.as_posix()]={'bytes':p.stat().st_size,'sha256':h(p)}
 assert expected==man,(name,'source manifest mismatch')
 seen=set();total=0
 with tarfile.open(target,'r:gz') as archive:
  for member in archive:
   n=member.name;parts=n.split('/');assert n and not PurePosixPath(n).is_absolute() and '\\' not in n and all(q not in ('','.','..') for q in parts)
   assert member.isfile() and not member.issym() and not member.islnk() and n not in seen and n in man,(name,n)
   seen.add(n);assert member.size==man[n]['bytes'];z=hashlib.sha256();size=0
   with archive.extractfile(member) as f:
    for block in iter(lambda:f.read(1024*1024),b''):z.update(block);size+=len(block)
   assert size==member.size and z.hexdigest()==man[n]['sha256'];total+=size
 assert seen==set(expected) and len(seen)==receipt['members']
 results[name]={'archive_bytes':receipt['bytes'],'archive_sha256':receipt['sha256'],'members':len(seen),'uncompressed_bytes':total,'source_set_manifest_tar_exact':True,'every_member_size_sha256_exact':True,'safe_relative_regular_unique_members':True,'excluded_counts':dict(skip)};allman[name]=man
 print(json.dumps({'name':name,'members':len(seen),'PASS':True}),flush=True)
required={'regression':['final/RESULT.json','final2cb/PARTIAL_RESULT.json','final5ed/RESULT.json','final47e/RESULT.json','final206/RESULT.json','final206/PROCESS_EXIT.json','final206/COLLECTION.json','final206/results.xml','final206/SUPPORTING_CHECKS.json','final206/source-before.json','final206/source-after.json','final206/executed-source-manifest.json','local-atomic-probe/RESULT.json','quality206/RESULT.json'],'review':['recovered/FINAL_206_TERMINAL_REVIEW.md','recovered/FINAL_206_TERMINAL_CHECKS.json','recovered/TRANSPORT_RECOVERY_206_REVIEW.md'],'integration':['TRANSPORT_RECOVERY_206.json','TERMINAL_AUDIT.json','FROZEN.json','LOCAL_ATOMIC_PROBE_AUDIT.json'],'route-before':['stdout','stderr','results.xml'],'route-fixed':['stdout','results.xml'],'budget-cleanup-probe':['RESULT.json'],'pb-heartbeat-diagnostic':['RESULT.json','PROCESS_EXIT.json']}
for root,paths in required.items():assert all(p in allman[root] for p in paths),(root,'required missing')
assert not {'PACKAGE_RESULT.json'}&set(allman['integration'])
out={'snapshot':'normal-push-before-snapshot','source_sha':'206de555e22c9a6e85c1ea87a33c1e55c0780968','archives':16,'total_members':sum(x['members'] for x in results.values()),'ARCHIVES_sha256':h(D/'ARCHIVES.json'),'results':results,'required_history_final_probe_quality_review_recovery_present':True,'central_written_by_reviewer':False,'tests_or_diagnostics_run':False,'push_receipt':'NOT_YET_REVIEWED_EXTERNAL_LATER'}
(O/'ARCHIVE_CHECKS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'archives':16,'members':out['total_members'],'all_exact':True}))
