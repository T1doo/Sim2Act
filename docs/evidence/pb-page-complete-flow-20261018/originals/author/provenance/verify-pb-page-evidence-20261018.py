"""Pure artifact verification; does not run product/Worker/browser/model."""
import hashlib,json,re,subprocess,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/Sim2Act'); dest=root/'docs/evidence/pb-page-complete-flow-20261018'
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((dest/'raw-manifest.json').read_text()); parts_count=0
with tarfile.open(dest/'raw-evidence.tar.gz') as tar:
 members={m.name:m for m in tar.getmembers()}; assert len(members)==len(manifest)
 for rec in manifest:
  rel=rec['path'];data=(dest/'originals'/rel).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256'];assert tar.extractfile(members[rel]).read()==data
  parts=rec.get('text_parts',[])
  if parts:
   blobs=[];offset=0
   for p in parts:
    b=(dest/p['path']).read_bytes();b.decode('utf-8');assert p['start_byte']==offset and p['end_byte']==offset+len(b) and p['bytes']==len(b) and sha(b)==p['sha256'];offset=p['end_byte'];blobs.append(b);parts_count+=1
   assert b''.join(blobs)==data
summary=json.loads((dest/'package-summary.json').read_text());assert summary['raw_files']==len(manifest) and summary['raw_bytes']==sum(r['bytes'] for r in manifest);assert sha((dest/'raw-evidence.tar.gz').read_bytes())==summary['bundle_sha256']
author=dest/'originals/author';before=json.loads((author/'inputs-before.json').read_text());after=json.loads((author/'inputs-after.json').read_text());assert before['inputs']==after['inputs'] and len(before['inputs'])==679
freeze=before['head'];prod=0
for path,rec in before['inputs'].items():
 data=(root/path).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256'];assert subprocess.check_output(['git','-c','core.fsmonitor=false','show',freeze+':'+path],cwd=root)==data
 if path.startswith('src/'):
  prod+=1;assert subprocess.check_output(['git','-c','core.fsmonitor=false','show','f5d6cedb26fe549ad274951892a219c0b34b32b9:'+path],cwd=root)==data
assert prod==132
xml=ET.parse(author/'full-pb.xml').getroot();cases=list(xml.iter('testcase'));assert len(cases)==1
for c in cases:assert c.find('failure') is None and c.find('error') is None and c.find('skipped') is None
case=author/'full-pb/test_successful_source_to_pb_d0';page=json.loads((case/'result.json').read_text());assert page['status']=='PASS' and len(page['checks'])==63
end=json.loads((case/'progress-summary.json').read_text());assert end['latest']['passed'] and not end['watchdog_fired'] and end['error_count']==0 and end['provider_requests']==3 and end['runtime_requests']==1
for name,count in [('source-generation-wire.json',3),('source-worker-wire.json',1),('runtime-wire.json',1)]:assert len(json.loads((case/name).read_text()))==count
http=list((case/'http').glob('*-metadata.json'));assert len(http)==end['http_responses']
for p in http:
 rec=json.loads(p.read_text());data=(case/rec['response_file']).read_bytes();assert sha(data)==rec['response_sha256'] and len(data)==rec['response_bytes']
links=0
for md in [dest/'README.md',dest/'READABLE.md',root/'docs/F2/PBCurrentPageCompletion20261018.md']:
 for link in re.findall(r'\]\(([^)]+)\)',md.read_text()):
  if link.startswith(('http://','https://','#')):continue
  assert (md.parent/link.split('#')[0]).resolve().exists(),(str(md),link);links+=1
result={'status':'PASS','classification':'PURE_ARTIFACT_AND_BYTE_VERIFICATION_NOT_PRODUCT_CASES','raw_files':len(manifest),'raw_bytes':summary['raw_bytes'],'tar_members_exact_bytes':len(members),'text_parts_reconstructed':parts_count,'local_links_checked':links,'execution_inputs_equal':679,'production_equal_to_accepted_f5':prod,'unique_pytest_pass_cases':1,'original_cjs_checks':len(page['checks']),'page_api_requests':len(page['requests']),'page_actions':len(page['actions']),'served_assets':len(page['static_resource_loads']),'boots':page['boots'],'original_http_bodies':len(http),'mock_requests':{'generation':3,'source':1,'pb_runtime':1},'real_models':0,'suites':[s.attrib for s in xml.iter('testsuite')],'limitations':'Owner entry only/PENDING; first PB v1, not v1-to-v2. No new native/PG/CI/real model/semantic qualification or canceled timing window.'}
(dest/'artifact-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
