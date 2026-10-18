import hashlib,json,re,subprocess,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/Sim2Act'); dest=root/'docs/evidence/pa-page-complete-flow-20261018'
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((dest/'raw-manifest.json').read_text()); names=set(); parts_count=0
with tarfile.open(dest/'raw-evidence.tar.gz') as tar:
 members={x.name:x for x in tar.getmembers()}; assert len(members)==len(manifest)
 for rec in manifest:
  rel=rec['path'];assert rel not in names;names.add(rel);data=(dest/'originals'/rel).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256'];assert tar.extractfile(members[rel]).read()==data
  parts=rec.get('text_parts',[])
  if parts:
   contents=[];offset=0
   for p in parts:
    b=(dest/p['path']).read_bytes();b.decode('utf-8');assert p['start_byte']==offset and p['end_byte']==offset+len(b) and p['bytes']==len(b) and sha(b)==p['sha256'];offset=p['end_byte'];contents.append(b);parts_count+=1
   assert b''.join(contents)==data
summary=json.loads((dest/'package-summary.json').read_text());assert summary['raw_files']==len(manifest) and summary['raw_bytes']==sum(r['bytes'] for r in manifest);assert sha((dest/'raw-evidence.tar.gz').read_bytes())==summary['bundle_sha256']
before=json.loads((dest/'originals/author/inputs-before.json').read_text());after=json.loads((dest/'originals/author/inputs-after.json').read_text());assert before['inputs']==after['inputs'] and len(before['inputs'])==139
for path,rec in before['inputs'].items():
 data=(root/path).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256'];assert subprocess.check_output(['git','-c','core.fsmonitor=false','show','c958a679f527bd209ff2916bee2f4c1a9eb771ba:'+path],cwd=root)==data
prod=[p for p in before['inputs'] if p.startswith('src/')];assert len(prod)==132
for p in prod:assert subprocess.check_output(['git','-c','core.fsmonitor=false','show','cac7941062592df0a65783a9c147b06c22c7fd1b:'+p],cwd=root)==(root/p).read_bytes()
cases=[];suites=[]
for fn in ['full-pa.xml','shared.xml']:
 t=ET.parse(dest/'originals/author'/fn).getroot();suites +=[s.attrib for s in t.iter('testsuite')]
 for c in t.iter('testcase'):assert c.find('failure') is None and c.find('error') is None and c.find('skipped') is None;cases.append((c.attrib.get('classname'),c.attrib['name']))
assert len(cases)==len(set(cases))==4
case=dest/'originals/author/full-pa/test_natural_spec_page_actual_0';page=json.loads((case/'results.json').read_text());assert len(page['checks'])==32;assert len(page['requests'])==94 and len(page['static_resource_loads'])==54
end=json.loads((case/'progress-summary.json').read_text());assert end['latest']['passed'] and not end['watchdog_fired'] and end['error_count']==0 and end['provider_requests']==3 and end['runtime_requests']==2
assert sha((case/'fixture.db').read_bytes())=='0141f8b68de2f6625ca6482673b93518279ec8d110138c6a0776b77e6823be25'
indroot=dest/'originals/independent'; indmanifest=json.loads((indroot/'final-deliverables-manifest.json').read_text())
# Independent author defines its own manifest shape; every copied raw file was verified above.
links=0
for md in [dest/'README.md',dest/'READABLE.md',root/'docs/F2/PANaturalPageCompletion20261018.md']:
 for link in re.findall(r'\]\(([^)]+)\)',md.read_text()):
  if link.startswith(('http://','https://','#')):continue
  target=(md.parent/link.split('#')[0]).resolve();assert target.exists(),(str(md),link);links+=1
result={'status':'PASS','raw_files':len(manifest),'raw_bytes':summary['raw_bytes'],'tar_members_exact_bytes':len(members),'text_parts_reconstructed':parts_count,'readable_local_links_checked':links,'source_inputs_equal':139,'production_equal_to_cac_freeze':132,'unique_pytest_pass_cases':4,'full_original_cjs_checks':32,'captured_original_http_bodies':end['http_responses'],'full_qualified_database_sha256':'0141f8b68de2f6625ca6482673b93518279ec8d110138c6a0776b77e6823be25','suites':suites,'limitations':'Pure artifact and byte verification, not additional product test cases or native/semantic/model qualification.'}
(dest/'artifact-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
