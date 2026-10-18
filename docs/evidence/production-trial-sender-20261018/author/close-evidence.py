from pathlib import Path
import ast,hashlib,json,os,subprocess,xml.etree.ElementTree as ET
repo=Path('/workspace/Sim2Act');root=Path('/workspace/production-trial-sender-20261018');out=root/'run-1'
assert not (root/'sealed-manifest.json').exists()
def sha(b):return hashlib.sha256(b).hexdigest()
execution=json.loads((out/'execution.json').read_text());assert execution['exit_code']==0
before=json.loads((out/'inputs-before.json').read_text());after=json.loads((out/'inputs-after.json').read_text());assert before==after
assert len(before['inputs'])==705 and sum(p.startswith('src/') for p in before['inputs'])==137
for name,e in before['inputs'].items():
 b=(repo/name).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
assert (out/'helpers-before.json').read_bytes()==(out/'helpers-after.json').read_bytes()
suite=ET.parse(out/'junit.xml').getroot();cases=list(suite.iter('testcase'))
assert len(cases)==8 and len({(c.attrib['classname'],c.attrib['name']) for c in cases})==8 and not any(list(c) for c in cases)
guard=json.loads((out/'offline-guard.json').read_text());assert guard['attempts']==[]
raw=[];physical=[]
for directory,dirs,names in os.walk(out/'actual-tmp',followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink()]
 for name in names:
  p=Path(directory)/name
  if p.is_symlink():continue
  if p.suffix=='.db':physical.append(dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())))
  else:raw.append(p)
assert len(physical)==8
states=[json.loads(p.read_text()) for p in raw if p.name=='sender-state.json'];assert len(states)==6
assert all(s['current_worker_live_enabled'] is False and s['protected_tables_strict_equal'] for s in states)
processes=[];crashed=[];recoveries=[]
for p in raw:
 if p.name=='process-window-proof.json':processes.append(json.loads(p.read_text()))
 if p.name=='crashed-sender.stdout':crashed.append([json.loads(line) for line in p.read_text().splitlines()])
 if p.name=='fresh-recovery.stdout':recoveries.append([json.loads(line) for line in p.read_text().splitlines()])
assert len(processes)==len(crashed)==len(recoveries)==2
assert {(d['phase'],d['planned_crash_exit'],d['actual_mock_handler_calls']) for d in processes}=={('marker-before-adapter',17,0),('received-before-archive',23,1)}
for p in processes:
 assert p['after_recovery_all_55_tables_strict_equal'] and p['fresh_recovery_adapter_calls']==0
 slot=p['pending']['ledger']['slots'][0]
 assert slot['attempted'] and slot['settlement'] is None and p['pending']['revision']==2
for records in crashed:
 assert records[0]['event']=='actual-child-claim' and records[-1]['io']==[]
for records in recoveries:
 d=records[-1];assert d['event']=='recovered-history' and d['sent']==d['methods']==d['io']==[]
parent_adapters=guard['adapter_methods'].count('request_serialized_captured')
child_adapters=sum(records[-1]['methods'].count('request_serialized_captured') for records in crashed)
parent_mock=sum(s['mock_handler_calls'] for s in states)
child_mock=sum(p['actual_mock_handler_calls'] for p in processes)
assert (parent_adapters,child_adapters,parent_mock,child_mock)==(5,1,4,1)
prior=json.loads(Path('/workspace/production-trial-journal-20261018/run-1/inputs-after.json').read_text())['inputs']
changed=[name for name,e in prior.items() if sha((repo/name).read_bytes())!=e['sha256']]
assert changed==['src/sim2act/production_trial_journal.py']
bridge=json.loads((root/'journal-extraction-bridge.json').read_text());assert bridge['after_sha256']==sha((repo/changed[0]).read_bytes())
importers=[]
for p in (repo/'src/sim2act').glob('*.py'):
 for node in ast.walk(ast.parse(p.read_text())):
  if isinstance(node,ast.ImportFrom) and (node.module and 'production_trial_sender' in node.module or any(a.name=='production_trial_sender' for a in node.names)):
   importers.append(str(p.relative_to(repo)))
  elif isinstance(node,ast.Import) and any('production_trial_sender' in a.name for a in node.names):importers.append(str(p.relative_to(repo)))
assert importers==[]
value=dict(source_commit=execution['source_commit'],baseline='94fa765de11e1e3cc42dac9070a28ec9c2b47647',unique_nodes=8,executions=8,passed=8,failed=0,junit_seconds=float(next(suite.iter('testsuite')).attrib['time']),outer_seconds=execution['elapsed_seconds'],inputs=705,production_inputs=137,input_drift=False,helper_drift=False,unchanged_baseline_inputs=702,unchanged_baseline_production=135,changed_baseline_inputs=changed,journal_mutation_and_validation_ast_bridged=True,production_importers=importers,physical_fixture_databases=physical,real_processes=4,planned_sender_exits=[17,23],fresh_recovery_exits=[0,0],process_windows=processes,parent_synthetic_adapter_calls=parent_adapters,child_synthetic_adapter_calls=child_adapters,total_synthetic_adapter_calls=parent_adapters+child_adapters,total_mock_handler_calls=parent_mock+child_mock,real_provider_calls=0,new_live_permits=0,worker_once_calls=0,worker_settings_live_enabled=False,existing_internal_adapter='configured_provider retains its pre-existing synthetic token/live adapter settings only with exact MockTransport; no real credential or environment read',old_19_and_12_nodes_rerun=0,capture_journal_atomicity='new capture two mirrors + existing journal/cursor four mirrors in one transaction; stale quota CAS rolls all six attempted writes back to already committed marker checkpoint',cancel_window='before wire guard: zero mock handler; after guard: one may-have-sent mock handler, late known body retained but accepted=false/halt; no external IO atomicity claim',row_evidence='strict full-row assertions in tests; mirror fingerprints/receipts exported, not full-row DB export. Final ordinary-fixture protection excludes runs/events intentionally changed by controls and claims. Normal and EMPTY tests intentionally corrupt new journal/capture pairs after saving valid receipts to prove fail-closed validators.',not_run=['real network/provider/model/account/fees/semantics','production source producer or LIVE sender installation','full generation/source/cold/UI chain','PostgreSQL SQL/concurrency','Windows/native','remote CI','old 19/12 matrices or old cancelled installation window'])
(root/'closure.json').write_text(json.dumps(value,indent=2)+'\n')
(root/'close-evidence.py').write_bytes(Path(__file__).read_bytes())
files={}
for directory,dirs,names in os.walk(root,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink() and d!='__pycache__']
 for name in names:
  p=Path(directory)/name
  if p.is_symlink() or p.suffix in ('.db','.pyc'):continue
  b=p.read_bytes();files[str(p.relative_to(root))]=dict(bytes=len(b),sha256=sha(b))
manifest=dict(scope='SEALED author design, source and qualification; all nonDB regular files excluding this manifest/bytecode/symlink aliases; stop writes after seal',files=files,files_excluding_manifest=len(files),bytes_excluding_manifest=sum(e['bytes'] for e in files.values()))
p=root/'sealed-manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(source=execution['source_commit'],passed=8,junit_seconds=value['junit_seconds'],files=len(files),bytes=manifest['bytes_excluding_manifest'],manifest_sha256=sha(p.read_bytes()),actual_synthetic_adapter_calls=6,actual_mock_handler_calls=5,real_provider_calls=0)))
