import gzip,hashlib,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
ROOT=Path('/workspace/Sim2Act');E=ROOT/'docs/evidence/run-private-read-scope-20261011';OUT=Path('/tmp/run-private-read-final-addendum-independent-20261011')
required=['full-exit.json','full-ui.xml','final-summary.json','frozen-before.json','frozen-after.json']
assert all((E/x).is_file() for x in required),'Incomplete terminal evidence'
summary=json.loads((E/'final-summary.json').read_text());ex=json.loads((E/'full-exit.json').read_text());select=json.loads((E/'selection.json').read_text());part=json.loads((E/'partition.json').read_text());baseline=json.loads((E/'baseline.json').read_text())
assert len(ex['statuses'])==5 and {str(x['shard']) for x in ex['statuses']}=={'0','1','2','3','ui'} and all(x['exit_code']==0 for x in ex['statuses']) and ex['code_unchanged']
collected=[x for x in (E/'full-collection.log').read_text().splitlines() if x.startswith('tests/') and '::' in x]
supplement=[x for x in (E/'supplement-collection.log').read_text().splitlines() if x.startswith('tests/') and '::' in x]
assert len(collected)==len(set(collected))==1698 and len(supplement)==len(set(supplement))==32
assert set(collected)==set(part['nodes']) and not set(collected)&set(supplement)
expected=set(collected+supplement);original=set(select['original_nodes']);assert len(original)==650 and original<=expected
modules={x.split('::',1)[0] for x in expected};mods=sorted([(x[:-3].replace('/','.'),x) for x in modules],key=lambda x:len(x[0]),reverse=True)
def testcase_id(case):
 cl=case.get('classname');name=case.get('name')
 for prefix,path in mods:
  if cl==prefix:return path+'::'+name
  if cl.startswith(prefix+'.'):return path+'::'+cl[len(prefix)+1:].replace('.','::')+'::'+name
 raise AssertionError('Unknown JUnit module '+cl)
def parse(name):
 root=ET.parse(E/name).getroot();cases={};skips={};failures=[]
 for c in root.iter('testcase'):
  node=testcase_id(c);assert node not in cases,(name,node)
  state='ERROR' if c.find('error') is not None else 'FAIL' if c.find('failure') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS';cases[node]=state
  if state=='SKIP':skips[node]=c.find('skipped').get('message','')
  if state in ['FAIL','ERROR']:failures.append(node)
 declared=Counter()
 for s in root.iter('testsuite'):
  declared['tests']+=int(s.get('tests',0));declared['SKIP']+=int(s.get('skipped',0));declared['FAIL']+=int(s.get('failures',0));declared['ERROR']+=int(s.get('errors',0))
 assert declared['tests']==len(cases) and all(declared[k]==sum(x==k for x in cases.values()) for k in ['SKIP','FAIL','ERROR'])
 return cases,skips,dict(Counter(cases.values())),declared
allcases={};skips={};per={}
for name in ['full-0.xml','full-1.xml','full-2.xml','full-3.xml','full-ui.xml','supplement.xml']:
 cases,ss,counts,decl=parse(name);assert not set(cases)&set(allcases),(name,'duplicate testcase')
 allcases.update(cases);skips.update(ss);per[name]={'case_count':len(cases),'outcomes':counts,'declared':dict(decl),'sha256':hashlib.sha256((E/name).read_bytes()).hexdigest()}
assert set(allcases)==expected,'JUnit does not match exact collection IDs'
counts=dict(Counter(allcases.values()));oldcounts=dict(Counter(allcases[x] for x in original));assert counts=={'PASS':1664,'SKIP':66} and oldcounts=={'PASS':641,'SKIP':9}
assert summary['author_unique_selected_nodes']==1730 and summary['main_selected']==1698 and summary['supplement_selected']==32
assert all(summary['author_final_outcomes'][k]==counts.get(k,0) for k in ['PASS','SKIP','FAIL','ERROR'])
assert all(summary['original_650_outcomes'][k]==oldcounts.get(k,0) for k in ['PASS','SKIP','FAIL','ERROR'])
before=json.loads((E/'frozen-before.json').read_text());after=json.loads((E/'frozen-after.json').read_text());assert before==after and len(before)==401
assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==h for k,h in before.items())
oldfiles=baseline['old_evidence_files'];assert len(oldfiles)==141 and all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==h for k,h in oldfiles.items())
archives={}
for folder,tmp in [('independent','/tmp/run-private-read-independent-20261011'),('independent-performance','/tmp/run-private-read-performance-independent-20261011')]:
 transfer=json.loads((E/folder/'archive-transfer.json').read_text());assert len(transfer)==(37 if folder=='independent' else 17);facts=[]
 for name,entry in transfer.items():
  saved=(E/folder/name).read_bytes();raw=gzip.decompress(saved) if name.endswith('.gz') else saved
  assert hashlib.sha256(saved).hexdigest()==entry['archived_sha256'] and hashlib.sha256(raw).hexdigest()==entry['original_sha256']
  original_raw=(Path(tmp)/entry['source_name']).read_bytes();assert raw==original_raw
  facts.append({'archive':folder+'/'+name,'original_sha256':hashlib.sha256(raw).hexdigest(),'archived_sha256':hashlib.sha256(saved).hexdigest()})
 archives[folder]=facts
# Verify the UI source/budget/assertion bytes stayed exactly at the 2b baseline.
ui_sources={}
for name in part['ui_modules']:
 now=(ROOT/name).read_bytes();old=subprocess.check_output(['git','show',baseline['head']+':'+name],cwd=ROOT);assert now==old
 ui_sources[name]=hashlib.sha256(now).hexdigest()
for name in ['tests/csv_material_reuse.cjs','tests/csv_logic_reuse.cjs','tests/project_column_patches.cjs','tests/project_column_versions.cjs','tests/project_column_material_ui.cjs']:
 if (ROOT/name).exists():
  now=(ROOT/name).read_bytes();old=subprocess.check_output(['git','show',baseline['head']+':'+name],cwd=ROOT);assert now==old;ui_sources[name]=hashlib.sha256(now).hexdigest()
# Historical FAILs remain identifiable and are never summed into final PASS.
historical={}
for p in sorted(E.rglob('*.xml')):
 if p.name in per and p.parent==E:continue
 x=ET.parse(p).getroot();items=[]
 for c in x.iter('testcase'):
  f=c.find('failure');err=c.find('error')
  if f is not None or err is not None:items.append({'classname':c.get('classname'),'name':c.get('name'),'kind':'FAIL' if f is not None else 'ERROR','message':(f if f is not None else err).get('message','')})
 if items:historical[str(p.relative_to(E))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'failures':items}
assert set(['red-first.xml','red-second.xml','expanded.xml','edge-red.xml','current-ui-isolated.xml','prerequisite-interrupted/full-1.xml','prerequisite-interrupted/supplement.xml'])<=set(historical)
rawtrace=json.loads((ROOT/baseline['old_trace_path']).read_text());assert rawtrace[1091]['sql'].strip().endswith('FROM runs') and rawtrace[1097]['sql'].strip().endswith('FROM runs')
R={'status':'LIMITED FINAL EVIDENCE AUDIT PASS','scope':'Read-only terminal artifact audit, no test rerun; author nodes are not independent test executions','exact_main1698':True,'exact_supplement32':True,'unique_nodes1730':True,'author_outcomes':{k:counts.get(k,0) for k in ['PASS','FAIL','ERROR','SKIP']},'original650_outcomes':{k:oldcounts.get(k,0) for k in ['PASS','FAIL','ERROR','SKIP']},'per_junit':per,'skipped_case_reasons':skips,'frozen_files':len(before),'frozen_bytes_unchanged':True,'old141_bytes_unchanged':True,'archives_raw_and_stored_verified':archives,'UI_source_budget_assertion_baseline_equal':ui_sources,'historical_failures_preserved':historical,'original_private_read_conclusion':'RETRACTED','prior_59_separate':True,'prior_UI_timeout_causality':'STILL NOT ESTABLISHED; final serial pass does not erase timeouts/profile risk','execution':ex,'not_run':select['explicit_not_run_modules']+['PG/Windows/native actual environment','old actual_50b/actual_fab source upgrades','real/paid models','full P-A/P-B/AT10','semantic/owner acceptance','remote CI/deploy']}
(OUT/'result.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');(OUT/'testcase-outcomes.json').write_text(json.dumps(allcases,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':R['status'],'author_outcomes':R['author_outcomes'],'original650':R['original650_outcomes'],'frozen401':True,'old141':True,'archives37plus17':True,'history_fail_groups':len(historical)},ensure_ascii=False))
