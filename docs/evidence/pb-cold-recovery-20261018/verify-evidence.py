"""Pure byte/package verification, not an additional product test."""
import hashlib, json, re, subprocess, tarfile, xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/Sim2Act')
dest=root/'docs/evidence/pb-cold-recovery-20261018'
sha=lambda data: hashlib.sha256(data).hexdigest()
load=lambda path: json.loads(path.read_text())
canonical=lambda obj: json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
manifest=load(dest/'raw-manifest.json');parts_count=0
with tarfile.open(dest/'raw-evidence.tar.gz') as tar:
 members={m.name:m for m in tar.getmembers()};assert len(members)==len(manifest)
 for rec in manifest:
  rel=rec['path'];data=(dest/'originals'/rel).read_bytes()
  assert len(data)==rec['bytes'] and sha(data)==rec['sha256']
  assert tar.extractfile(members[rel]).read()==data
  parts=rec.get('text_parts',[])
  if parts:
   blobs=[];offset=0
   for part in parts:
    blob=(dest/part['path']).read_bytes();blob.decode('utf8')
    assert part['start_byte']==offset and part['end_byte']==offset+len(blob)
    assert part['bytes']==len(blob) and sha(blob)==part['sha256']
    offset=part['end_byte'];blobs.append(blob);parts_count+=1
   assert b''.join(blobs)==data
summary=load(dest/'package-summary.json')
assert summary['raw_files']==len(manifest) and summary['raw_bytes']==sum(r['bytes'] for r in manifest)
assert sha((dest/'raw-evidence.tar.gz').read_bytes())==summary['bundle_sha256']
author=dest/'originals/author';before=load(author/'inputs-before-retry.json');after=load(author/'inputs-after.json')
assert before['inputs']==after['inputs'] and len(before['inputs'])==681
freeze=before['head'];production=[]
for path,rec in before['inputs'].items():
 data=(root/path).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256']
 assert subprocess.check_output(['git','-c','core.fsmonitor=false','show',freeze+':'+path],cwd=root)==data
 if path.startswith('src/'):
  production.append(path)
assert len(production)==132
changed=[p for p in production if subprocess.check_output(['git','-c','core.fsmonitor=false','show','1f725e8318a9f3993e782335203d5b2e76085c0f:'+p],cwd=root)!=(root/p).read_bytes()]
assert changed==['src/sim2act/web/internal.js']
xmls=[ET.parse(author/name).getroot() for name in ['cold-suite-retry.xml','platform-parallel.xml','original-navigation.xml']]
cases=[case for xml in xmls for case in xml.iter('testcase')]
passed=[case for case in cases if case.attrib.get('name') and all(case.find(tag) is None for tag in ['failure','error','skipped'])]
unique_passed={(case.attrib.get('classname'),case.attrib['name']) for case in passed};assert len(unique_passed)==6
initial=ET.parse(author/'cold-suite.xml').getroot();assert len(list(initial.iter('testcase')))==5
assert len(list(initial.iter('error')))==5
initial_seed=author/'cold-suite/pb-cold-successful-source-seed0'
assert load(initial_seed/'model-wire.json')==load(initial_seed/'runtime-wire.json')==[]
suite=author/'cold-suite-retry';seed=suite/'pb-cold-successful-source-seed0'
assert len(load(seed/'model-wire.json'))==3 and len(load(seed/'runtime-wire.json'))==1
seed_copy=load(seed/'seed-copy-provenance.json');seed_bytes=(seed/'sealed-source.db').read_bytes()
assert sha(seed_bytes)==seed_copy['sealed_sha256']==seed_copy['original_sha256']
assert (seed/'fixture.db').read_bytes()==seed_bytes
claims=load(seed/'source-worker-claims.json')
assert claims['worker_calls']==1 and claims['lease_or_clock_mutations']==0
assert claims['before']['clock']==claims['after']['clock'] and len(claims['after']['claims'])==1
assert claims['after']['header']['status']=='SUCCEEDED'
assert claims['before']['header']['created_at']==claims['after']['header']['created_at']
totals=dict(checks=0,actions=0,page_api=0,served_assets=0,boots=0,http_originals=0)
page_rows=[]
parallel=author/'platform-parallel';parallel_seed=parallel/'pb-cold-successful-source-seed0'
assert len(load(parallel_seed/'model-wire.json'))==3 and len(load(parallel_seed/'runtime-wire.json'))==1
assert load(parallel_seed/'source-before.json')==load(parallel_seed/'source-after.json')
qualified_folders=[*sorted(suite.glob('test_pb_cold_original_extracti[0-3]')),parallel/'test_pb_cold_original_extracti0']
for folder in qualified_folders:
 page=load(folder/'page-result.json');proof=load(folder/'proof.json');progress=load(folder/'progress-summary.json')
 assert page['status']==proof['status']=='PASS' and not page['page_errors']
 assert progress['latest']['passed'] and not progress['watchdog_fired'] and progress['error_count']==0
 assert page['worker_calls']==0 and proof['page_worker_calls']==0 and proof['accepted_extractions']==1
 assert load(folder/'source-before.json')==load(folder/'source-after.json')
 case_seed=parallel_seed if folder.parent==parallel else seed
 assert load(folder/'clone-provenance.json')['source_sha256']==sha((case_seed/'sealed-source.db').read_bytes())
 posts=[r for r in page['requests'] if r['method']=='POST' and r['path'].endswith('/extractions')]
 assert len(posts)==1 and posts[0]['status']==201
 ticket=page['ticket'];assert len(ticket)==17
 assert ticket['request_key']==posts[0]['body']['review']['request_key']
 assert sha(canonical(posts[0]['body']))==ticket['request_fingerprint']
 assert ticket['candidate_fingerprint']==posts[0]['response']['candidate_fingerprint']
 for asset in page['static_resource_loads']:
  assert asset['status']==200
  assert sha((root/'src/sim2act/web'/(asset['path'].lstrip('/') or 'index.html')).read_bytes())==asset['sha256']
 http=list((folder/'http').glob('*-metadata.json'));assert len(http)==progress['http_responses']
 barriers=load(folder/'authorization-barriers.json')
 assert len(barriers)==(1 if proof['scenario']=='boundary' else 0)
 for barrier in barriers:assert barrier['status']==403 and not barrier['blocked']
 if proof['scenario']=='navigation':
  digest=page['digest_observations'];assert len(digest)==1 and digest[0]['delivered']
  assert digest[0]['actual_result_computed_before_hold'] and digest[0]['actual_digest_hex']==ticket['request_fingerprint']
  assert sha(bytes.fromhex(digest[0]['input_hex']))==ticket['request_fingerprint']
 if proof['revoke_kind']=='source':
  faults=page['storage_faults'];assert len(faults)==1 and faults[0]['original_raw']==faults[0]['repair_raw']
  original=json.loads(faults[0]['original_raw']);fault=json.loads(faults[0]['fault_raw']);assert original['request_key']!=fault['request_key']
  fault['request_key']=original['request_key'];assert fault==original
 totals['checks']+=len(page['checks']);totals['actions']+=len(page['actions']);totals['page_api']+=len(page['requests'])
 totals['served_assets']+=len(page['static_resource_loads']);totals['boots']+=page['boots']
 page_rows.append(dict(batch=folder.parent.name,folder=folder.name,scenario=proof['scenario'],revoke_kind=proof['revoke_kind'],elapsed_seconds=progress['elapsed_seconds'],checks=len(page['checks'])))
assert len(page_rows)==5
for folder in [seed,*sorted(suite.glob('test_pb_cold_original_extracti[0-4]')),initial_seed,parallel_seed,parallel/'test_pb_cold_original_extracti0']:
 for meta in (folder/'http').glob('*-metadata.json'):
  rec=load(meta);data=(folder/rec['response_file']).read_bytes()
  assert sha(data)==rec['response_sha256'] and len(data)==rec['response_bytes']
  req=load(meta.with_name(meta.name.replace('-metadata.json','-request-bytes.json')))
  body=(folder/req['file']).read_bytes();assert sha(body)==req['sha256'] and len(body)==req['bytes']
  totals['http_originals']+=1
links=0
for md in [dest/'README.md',dest/'READABLE.md',root/'docs/F2/PBNaturalExtractionColdRecovery20261018.md']:
 for link in re.findall(r'\]\(([^)]+)\)',md.read_text()):
  if link.startswith(('http://','https://','#')):continue
  target=(md.parent/link.split('#')[0]).resolve()
  if target==dest/'artifact-verification.json':continue
  assert target.exists(),(str(md),link);links+=1
result=dict(status='PASS',classification='PURE_PACKAGE_BYTE_VERIFICATION_NOT_PRODUCT_CASES',raw_files=len(manifest),raw_bytes=summary['raw_bytes'],tar_members_exact_bytes=len(members),text_parts_reconstructed=parts_count,local_links_checked=links,execution_inputs_equal=681,production_count=132,changed_production=changed,unique_pytest_pass_cases=6,actual_http_jsdom_cases=5,synthesized_api_controller_regressions=1,initial_shared_seed_errors=5,initial_model_requests=0,actual_pass_records=len(passed),main_suite_summary=[s.attrib for s in xmls[0].iter('testsuite')],mock_requests=dict(generation=6,source=2,page=0),real_model_requests=0,scenarios=page_rows,totals=totals)
(dest/'artifact-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
