from pathlib import Path
import ast,hashlib,json,os,shutil,subprocess,xml.etree.ElementTree as ET
root=Path('/workspace/production-trial-journal-20261018');out=root/'run-1';repo=Path('/workspace/Sim2Act')
assert not (root/'sealed-manifest.json').exists()
execution=json.loads((out/'execution.json').read_text());assert execution['exit_code']==0
before=json.loads((out/'inputs-before.json').read_text());after=json.loads((out/'inputs-after.json').read_text());assert before==after
assert len(before['inputs'])==703 and sum(k.startswith('src/') for k in before['inputs'])==136
for name,e in before['inputs'].items():
 b=(repo/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
assert (out/'helpers-before.json').read_bytes()==(out/'helpers-after.json').read_bytes()
suite=ET.parse(out/'junit.xml').getroot();cases=list(suite.iter('testcase'))
assert len(cases)==12 and len({(c.attrib['classname'],c.attrib['name']) for c in cases})==12
assert not any(list(c) for c in cases)
assert json.loads((out/'offline-guard.json').read_text())['attempts']==[]
physical=[];raw=[]
for directory,dirs,files in os.walk(out/'actual-tmp',followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink()]
 for name in files:
  p=Path(directory)/name
  if p.is_symlink():continue
  if p.suffix=='.db':physical.append(dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  else:raw.append(p)
assert len(physical)==12
races=[json.loads(p.read_text()) for p in raw if p.name=='linearization.json']
assert len(races)==6
assert {(r['first'],r['change']) for r in races}=={(a,b) for a in ('marker','control') for b in ('cancel','lease','fence')}
for r in races:
 assert 'both-active-before-release' in r['trace']
 slot=r['settled']['ledger']['slots'][0]
 assert slot['attempted']==(r['first']=='marker') and not slot['accepted'] and slot['settlement']['total_tokens']==8
 assert r['settled']['ledger']['halted'] and r['independent_connections']==2
children=[]
for p in raw:
 if p.name in ('pending-child.stdout','unknown-child.stdout'):
  d=json.loads(p.read_text());assert d['io_attempts']==[] and d['duplicate']['duplicate'] and d['before']==d['after']
  children.append(dict(path=str(p.relative_to(root)),revision=d['after']['revision'],halted=d['after']['ledger']['halted'],attempted=d['after']['ledger']['slots'][0]['attempted']))
assert sorted(c['revision'] for c in children)==[1,3]
protected=json.loads(Path('/workspace/production-policy-kernel-followup-20261018/inputs-after.json').read_text())['inputs']
for name,e in protected.items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==e['sha256']
importers=[]
for p in (repo/'src/sim2act').glob('*.py'):
 for node in ast.walk(ast.parse(p.read_text())):
  if isinstance(node,ast.ImportFrom) and (node.module and 'production_trial_journal' in node.module or any(a.name=='production_trial_journal' for a in node.names)):
   importers.append(str(p.relative_to(repo)))
  elif isinstance(node,ast.Import) and any('production_trial_journal' in a.name for a in node.names):importers.append(str(p.relative_to(repo)))
assert importers==[]
value=dict(source_commit=execution['source_commit'],baseline='080ea7b184a7476019431c1803b4bfe4864afbd9',unique_nodes=12,executions=12,passed=12,failed=0,junit_seconds=float(next(suite.iter('testsuite')).attrib['time']),outer_seconds=execution['elapsed_seconds'],inputs=703,production_inputs=136,unchanged_baseline_inputs=701,unchanged_baseline_production=135,input_drift=False,helper_drift=False,production_importers=importers,journal_namespace='uninstalled-production-trial-journal.v1',new_tables=0,permission_changes=0,physical_fixture_databases=physical,actual_two_connection_orderings=6,new_process_reads=children,source_results='SYNTHETIC_INTERNAL_INPUTS_ONLY',provider_calls=0,new_live_permits=0,old_19_nodes_rerun=0,read_gap='Static WIP P2 fixed before freeze; no dynamic run of incorrect version',row_evidence='New journal mirror revisions/fingerprints; strict unchanged all other tables in ordinary cases. Fixture final strict other-table comparison excludes runs/events intentionally changed by actual control/fixture mutators. CAS negative all 55 tables exact equality. Not per-operation 55-table windows or independent DB reconstruction.',scope='SQLite durable journal and bounded contention only; pending/UNKNOWN real new-process reads; no sender or actual production Attempt',not_run=['PostgreSQL SQL/row-lock concurrency','Windows/native','remote CI','real source/account/fees/model/semantics','full source/cold/UI chain','old synthetic recovery matrix','old cancelled installation window'])
(root/'closure.json').write_text(json.dumps(value,indent=2)+'\n')
(root/'close-evidence.py').write_bytes(Path(__file__).read_bytes())
files={}
for directory,dirs,names in os.walk(root,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink() and d!='__pycache__']
 for name in names:
  p=Path(directory)/name
  if p.is_symlink() or p.suffix in ('.db','.pyc'):continue
  b=p.read_bytes();files[str(p.relative_to(root))]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
manifest=dict(scope='SEALED author design, qualification, raw nonDB files; excludes this manifest, bytecode and symlink aliases; no later writes',files=files,files_excluding_manifest=len(files),bytes_excluding_manifest=sum(x['bytes'] for x in files.values()))
p=root/'sealed-manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(source=execution['source_commit'],passed=12,files=len(files),bytes=manifest['bytes_excluding_manifest'],manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),junit_seconds=value['junit_seconds'])))
