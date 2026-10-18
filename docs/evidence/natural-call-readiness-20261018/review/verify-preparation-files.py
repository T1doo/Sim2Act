"""Pure file/Git preparation review. No product import, execution, model or DB."""
from pathlib import Path
import hashlib,json,stat,subprocess
root=Path('/workspace/natural-semantic-preparation-20261018');repo=Path('/workspace/Sim2Act')
review=Path('/workspace/natural-production-call-design-review-20261018')
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest_raw=(root/'MANIFEST.json').read_bytes();m=json.loads(manifest_raw)
assert sha(manifest_raw)=='0d551c953b5c86e92b010ada120556dce51b22cc2f3c3e3706c700914dfa38f3'
assert m['entry_count']==9 and m['total_pre_manifest_bytes']==23481 and len(manifest_raw)==1799
assert stat.S_IMODE(root.stat().st_mode)==0o555
verified=[]
for h in m['files']:
 p=root/h['path'];b=p.read_bytes()
 assert len(b)==h['bytes'] and sha(b)==h['sha256'] and len(b.decode().splitlines())==h['text_lines']
 assert stat.S_IMODE(p.stat().st_mode)==0o444
 verified.append(dict(path=h['path'],bytes=len(b),sha256=sha(b),lines=h['text_lines'],mode='0444'))
assert len(verified)==9 and sum(v['bytes'] for v in verified)==23481
assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}=={v['path'] for v in verified}|{'MANIFEST.json'}
for name,size in [('material_a.txt',454),('material_b.txt',519)]:
 b=(root/name).read_bytes();assert b.isascii() and b.endswith(b'\n') and b.count(b'\n')==5 and len(b)==size and len(b)<=1024
 assert len(b.decode().splitlines())==5
 assert b'REQUIREMENT' not in b and b'[REQ]' not in b
goals=json.loads((root/'goal_drafts.json').read_text());assert goals['status']=='UNBOUND_GOAL_DRAFTS_NOT_SUBMITTABLE'
assert len(goals['goals'])==2
fields={'title','goal','known','assumptions','unresolved','constraints','acceptance_checks','resource_refs'}
for case in goals['goals']:
 c=case['goal_card_draft'];assert set(c)==fields and 0<len(c['title'])<=200 and 0<len(c['goal'])<=4000
 for k in ['known','assumptions','unresolved','constraints','acceptance_checks']:
  assert isinstance(c[k],list) and len(c[k])<=16 and all(isinstance(x,str) and 0<len(x)<=1000 for x in c[k])
 assert c['resource_refs']==['__UNBOUND_ACTUAL_MATERIAL_'+case['case']+'_RESOURCE_ID__']
 assert case['material_file']=='material_'+case['case'].lower()+'.txt'
for suffix in ['a','b']:
 s=(root/('score_sheet_'+suffix+'.md')).read_text()
 assert 'EXECUTION_NOT_RUN / SEMANTIC_NOT_SCORED / OWNER_PENDING' in s
 assert s.count('| NOT_SCORED | NOT_PRODUCED | PENDING |')==5
 assert '加权分：NOT_SCORED' in s and '人工语义结论：PENDING' in s and '完整输出文件/hash | NOT_PRODUCED' in s
rubric=(root/'RUBRIC.md').read_text()
assert 'DRAFT_NOT_OWNER_CONFIRMED / SEMANTIC_NOT_SCORED' in rubric
assert '没有预设自动PASS阈值' in rubric
weights=[30,20,25,15,10];assert sum(weights)==100
reference=(root/'private_reference/semantic_reference_draft.md').read_text()
assert 'PRIVATE_REFERENCE_DRAFT / NOT_OWNER_CONFIRMED / NOT_MODEL_OUTPUT / NOT_AN_ACCEPTED_GOLD' in reference
provenance=json.loads((root/'provenance.json').read_text())
assert provenance['status']=='SEALED_CANDIDATE_PREPARATION_NOT_EXECUTED_NOT_SCORED'
assert provenance['materials_and_references_used_for_current_implementation_or_tests'] is False
assert provenance['private_reference_owner_confirmation']=='NOT_DONE' and provenance['root_needs_to_read_private_reference'] is False
assert provenance['blind_holdout_qualification'].startswith('NOT_ESTABLISHED')
context=[]
for h in provenance['read_only_context_sources']:
 p=repo/h['path'];b=p.read_bytes()
 context.append({'path':h['path'],'recorded_sha256':h['sha256'],'recorded_bytes':h['bytes'],'current_bytes_equal':len(b)==h['bytes'] and sha(b)==h['sha256']})
git=lambda *args:subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo,text=True)
assert git('rev-parse','HEAD').strip()=='5a348ce97325ebbe450c2beb09dff767a4376252'
assert git('diff','--name-only','5a348ce97325ebbe450c2beb09dff767a4376252','--','src','tests')==''
result=dict(status='PREPARATION_METADATA_AND_STATIC_CONTENT_CONSISTENCY_CHECKED_NOT_EXECUTED_NOT_SCORED',
 design_decision='NO_SAFE_INDEPENDENT_PRODUCTION_SLICE',baseline='5a348ce97325ebbe450c2beb09dff767a4376252',
 source_and_tests_unchanged=True,manifest_path=str(root/'MANIFEST.json'),manifest_sha256=sha(manifest_raw),
 prepared_entries=9,pre_manifest_bytes=23481,manifest_bytes=1799,total_regular_files=10,total_regular_file_bytes=25280,
 files=verified,prepared_goals=2,goal_resource_binding='UNBOUND_PLACEHOLDERS_NOT_SUBMITTABLE',materials_ascii_bytes=[454,519],material_lines=[5,5],
 rubric='Draft 5 dimensions totaling100; no automatic PASS threshold; source-owner confirmation absent',score_sheets='Two empty NOT_SCORED/PENDING sheets; no tested output exists',
 private_reference='Read by this reviewer for preparation consistency only; not an accepted gold, no output scoring performed; answer content not copied into this report',
 independence='NOT_ESTABLISHED as blind holdout; preparer saw development fixtures and all references, this reviewer also read references; record future exposure',
 content_conclusion='No definite internal preparation contradiction found. Task-specific Goal constraints are part of future declared task, not proof of blind discovery or independent model performance.',
 context_file_checks=context,source_qualification='No new OfflineSoftwareQualification object/pin, no self-approval code, no calls or policy relaxation',
 not_run=['product','pytest','HTTP/API','Worker/MockModel/target model','DB/SQL','network','credentials/fee/source discovery','human semantic/output scoring','owner acceptance','P-A/P-B execution','Windows/native','PG','CI'],
 source_directory_written=False,old_sealed_directories_written=False)
with (review/'preparation-verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['files','context_file_checks']},ensure_ascii=False,indent=2))
