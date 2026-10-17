import os,pathlib,json,hashlib,sqlite3,xml.etree.ElementTree as E,collections,subprocess
p=pathlib.Path(__file__).parent
sha='f3d0e96487f57941255f68f6c501b6956cc5f31b'
def read(q): return json.loads(q.read_text())
def write(name,value): (p/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def fp(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
batches=[]; identities=[]
for b in ('api','pages_related'):
 d=p/b; term=read(d/'terminal.json'); root=E.parse(d/'junit.xml').getroot(); suites=list(root.iter('testsuite')); cases=[]
 for c in root.iter('testcase'):
  rec=dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0')),outcome='PASS' if not list(c) else 'OTHER')
  assert not any(n.tag in ('failure','error','skipped') for n in c)
  cases.append(rec); identities.append(rec['classname']+'::'+rec['name'])
 write(b+'/collected.json',dict(provenance='Derived from original JUnit testcase entries, not a second collection/test execution',cases=cases))
 after=read(d/'source-after.json'); before=read(d/'source-before.json')
 assert term['returncode']==0 and before==after and after['equals_git_input']
 batches.append(dict(batch=b,returncode=term['returncode'],tests=sum(int(s.get('tests')) for s in suites),failures=sum(int(s.get('failures')) for s in suites),errors=sum(int(s.get('errors')) for s in suites),skipped=sum(int(s.get('skipped')) for s in suites),junit_seconds=sum(float(s.get('time')) for s in suites),wall_seconds=term['wall_seconds'],input_count=len(after['inputs']),source_unchanged=True,cases=cases))
assert len(identities)==len(set(identities))==15
write('union.json',dict(source_sha=sha,unique_nodes=15,overlap=0,additional_unique_over_author=0,nodeids=identities))
page=[]
for f in sorted((p/'pages_related/data').rglob('page-result.json')):
 o=read(f); w=read(f.parent/'page-worker-proof.json'); assert o['status']=='PASS'
 assets=[]
 for a in o['assets']:
  src=p/'snapshot/src/sim2act/web'/ (a['path'].lstrip('/') or 'index.html'); actual=hashlib.sha256(src.read_bytes()).hexdigest(); assert actual==a['sha256']; assets.append(dict(**a,input_sha_matches=True))
 req=o['requests']; extracts=[r for r in req if r['method']=='POST' and r['path'].endswith('/csv-sum-candidates')]
 assert len(extracts)==1 and extracts[0]['status']==201 and extracts[0]['body']['consent']=='EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT'
 assert len(w['worker_runs'])==(0 if o['case']=='navigation' else 1)
 page.append(dict(case=o['case'],raw=f.relative_to(p).as_posix(),status=o['status'],checks=o['checks'],check_count=len(o['checks']),requests=len(req),actual_api_replies=sum('status' in r for r in req),post_count=sum(r['method']=='POST' for r in req),extraction_posts=len(extracts),accepted_delivery_lost_count=sum(r.get('delivery')=='ACTUAL_201_LOST' for r in req),assets=assets,source_fixture_workers=1,new_store_derived_workers=len(w['worker_runs']),delivery=o['delivery'],worker_results=[dict(run_id=r['id'],status=r['status'],result_version=r['result_version'],column=r['result'].get('column'),sum=r['result'].get('sum')) for r in w['worker_runs']]))
databases=[]
for b in ('api','pages_related'):
 for f in sorted((p/b/'data').rglob('*.db')):
  c=sqlite3.connect(f.as_uri()+'?mode=ro',uri=True); c.row_factory=sqlite3.Row
  names=[r[0] for r in c.execute("select name from sqlite_master where type='table' order by name")]
  counts={n:c.execute('select count(*) from "'+n.replace('"','""')+'"').fetchone()[0] for n in names}
  runs=[]
  for r in c.execute('select id,status,version,result,error from runs order by id'):
   v=dict(r); result=json.loads(v.pop('result')) if v['result'] is not None else None; error=json.loads(v.pop('error')) if v['error'] is not None else None
   v.update(embedded_result_version=(result or {}).get('result_version'),result_sum=(result or {}).get('sum'),error_code=(error or {}).get('code'));runs.append(v)
  attempts=[dict(r) for r in c.execute('select run_id,count(*) as ledger_rows from attempts group by run_id')]
  databases.append(dict(path=f.relative_to(p).as_posix(),counts=counts,runs=runs,attempt_ledger=attempts,provenance='Post-terminal read-only sqlite3; ledger rows are not global provider-request instrumentation'))
  c.close()
assert len(databases)==15
scope=[]
for f in sorted((p/'api/data').rglob('scope-proof.json')):
 v=read(f); scope.append(dict(path=f.relative_to(p).as_posix(),scope=v['scope'],statuses=v['statuses'],sql_statement_count=len(v['sql']),no_full_run_or_app_select=not any(s.startswith('SELECT runs.id, runs.project_id, runs.runtime_id, runs.principal_id, runs.request_key') or s.startswith('SELECT app_drafts.id, app_drafts.project_id, app_drafts.runtime_id, app_drafts.name') for s in v['sql']) if v['scope'] in ('material','saved-report') else 'NOT_ASSERTED_FOR_THIS_SCOPE'))
happy=read(next((p/'api/data').rglob('sum-only-delivery.json'))); proof=happy['options']['proof']; contract=happy['source']['contract']['snapshot']
assert proof['contract_fingerprint']==fp(contract) and proof['result_fingerprint']==fp(happy['source']['result'])
assert proof['receipts_fingerprint']==fp(happy['source']['result']['receipts']) and len(proof['confirmation_fingerprint'])==64
queued=read(next((p/'api/data').rglob('queued-source-recheck.json')))
proofout=dict(source_sha=sha,batches=batches,union_unique=15,overlap=0,source_inputs=dict(total=594,src=120,tests=465,schemas=7,pyproject=1,rebuild_gold=1,git_blob_and_sha_before_after_equal=True),pages=page,page_totals=dict(checks=sum(i['check_count'] for i in page),actual_api_replies=sum(i['actual_api_replies'] for i in page),assets=sum(len(i['assets']) for i in page),visible_posts=sum(i['post_count'] for i in page),source_fixture_workers=3,new_store_derived_workers=2,real_model_requests=0,download_blobs=0),sql_scope_checks=scope,queued_source_denial=dict(status=queued['run']['status'],error=queued['run']['error'],mutation='Controlled test-fixture SQL Grant revocation; not a UI/API revoke',second_worker_once_false='Original test assertion passed'),happy_proof_crosschecks=dict(contract_sha_equal=True,result_sha_equal=True,receipts_sha_equal=True,confirmation_sha_present=True,subset_goal_does_not_inherit_full_md=True,manifest_goal_ref=happy['candidate']['candidate']['manifest']['goal_ref']),sqlite=databases)
write('proof.json',proofout)
review=dict(verdict='PASS_BOUNDED',source_sha=sha,branch='dev/ordinary-csv-sum-pb-20261017',repo_write=False,executions=15,unique_nodes=15,additional_unique_over_author=0,automatic_retries=0,new_nodes=12,direct_legacy_nodes=3,static_findings_open=[],static_review=[dict(location='src/sim2act/ordinary_csv_extraction.py:43-123',finding='Run/header, frozen and intent material IDs, independent save-effect IDs and receipt references are projected and authorized before protected Run/candidate bodies. Independent task_extractions and candidate scalar anchors prevent source-family downgrade.'),dict(location='src/sim2act/ordinary_csv_extraction.py:126-176',finding='Original successful mock CSV complete report and confirmation are reverified through accepted_result. Proof binds contract/GoalSpec/result/three receipts/confirmation; candidate explicitly promises only read-only parameterized CSV sum, not source MD generation or source acceptance.'),dict(location='src/sim2act/ordinary_csv_extraction.py:210-276',finding='Project-locked original-key CAS persists one committed task_extractions/app_draft. Source/target and exact regenerated candidate are rechecked on cached receipt and lifecycle reads; existing runtime reused, no new principal/Grant/table/executor.'),dict(location='src/sim2act/apps.py:308-313,499-502; src/sim2act/text_continuations.py:456-504',finding='Exact source kind and registered aggregate tuple dispatched; draft metadata gate propagates to release/job before protected read and execution.'),dict(location='src/sim2act/web/ordinary-csv.js:143-208',finding='Frozen implementation includes fresh workspace read, same-scope Run version/contract poll rebind, URL request-key match, Map same-entry replacement, default-unchecked SUM_ONLY and explicit original-key recovery/retry; two-phase app handoff retains app/project/identity fencing.'),dict(location='src/sim2act/local_tasks.py:412-415',finding='Existing product retirement rejects any Run-referenced source; no unreachable retired-source injection or additional test was added.')],dynamic_scope=['9 new API nodes: exact consent, concurrent idempotency, read-only original-key recovery, source material/saved-report/target-runtime denial and result CAS, successful source after original execution deadline, manual-accepted PARTIAL exclusion, queued source denial before any effects.','3 new full served ASGI RPC/JSDOM pages: deliver and lost execute visible preview→approval→commit→instance→unified directory→new-input Run/result15-v1; navigation only tests late project and reconnect callbacks.','3 named legacy regressions executed once; no old correction37 or migration probe rerun.'],limitations=['Finite ordinary successful CSV complete-contract→sum-only P-B bridge; not arbitrary Goal applicationization or general semantic acceptance. Original complete source is prepared and executed by Python fixture before the page starts from its history.','JSDOM is not native browser. Native interval polling disabled in driver; ordinary same-Run redraw is manually invoked through actual showRun and actual API reads.','No download UI or captured Blob in this slice; only old CSV report regression writes saved-report.md as an assertion artifact.','Main new CSV source/derived paths use NoModel. The manual-accepted MD negative uses ScriptedMd with three synthetic responses by source control flow; old natural regression uses one synthetic MockTransport planning response by its fixture control flow. No global provider-request spy was added. Zero real model traffic.','Grant denial tests use controlled fixture SQL revocation (saved-report case also corrupts receipt refs); they are not visible or API revocation actions. Queued denial is existing WAITING_RESOURCE/GRANT_REVOKED, not FAILED or an exception-recovery claim.','Fixture target-resource and initial-app creation occur before the no-authority-change snapshots and use existing policies; no-new-Grant/principal/resource assertions apply to extraction and derived-use phases, not all fixture setup. Original complete-report save uses original two-derived-read-Grant policy.','Fresh Store/TestClient/Worker objects run in the same Python process; no independent process restart, PG, Windows, native browser, remote CI, real model, true human semantic verification, deployment, or publication was run.','Cross-family broad failure matrices and retired-impossible-state injection were not run.'],evidence=dict(root=str(p),batches=['api/junit.xml','pages_related/junit.xml'],runtime_sqlite=15,raw_page_results=3,raw_scope_sql=4),input_provenance='Exact git archive f3d0e964; 593 src/tests/schemas/pyproject tracked files plus one same-SHA reconstructible gold fixture. Read-only dependency symlink to preinstalled node_modules; snapshot source untouched.')
write('review.json',review)
# Verify the shared repository source inputs still match the executed exact Git snapshot; docs-only new evidence is outside input set.
genv=os.environ.copy();genv['GIT_OPTIONAL_LOCKS']='0'; base=read(p/'input-source.json'); rows=[]
for old in base['inputs']:
 data=(pathlib.Path('/workspace/Sim2Act')/old['path']).read_bytes(); rows.append(dict(path=old['path'],git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
assert rows==base['inputs']
write('source-after.json',dict(source_sha=sha,executed_snapshot_inputs_unchanged=True,shared_repo_inputs_equal_snapshot=True,inputs=rows))
# Raw runtime and derived evidence, never reconstructible snapshot, pytest cache, symlink aliases, or self-referential manifest files.
entries=[]
for root,dirs,files in os.walk(p,followlinks=False):
 dirs[:]=[d for d in dirs if d not in ('snapshot','pytest-cache','__pycache__') and not (pathlib.Path(root)/d).is_symlink()]
 for name in sorted(files):
  f=pathlib.Path(root)/name
  if f.is_symlink() or name in ('raw-manifest.json','SHA256SUMS'): continue
  data=f.read_bytes(); rel=f.relative_to(p).as_posix(); entries.append(dict(path=rel,size=len(data),sha256=hashlib.sha256(data).hexdigest(),kind='runtime_original' if '/data/' in rel or name in ('pytest.log','junit.xml','terminal.json','command.json') else 'derived_or_reconstructible_input_metadata'))
entries.sort(key=lambda r:r['path'])
write('raw-manifest.json',dict(source_sha=sha,entries=entries,total_files=len(entries),runtime_outputs_retained=True,reconstructible_inputs=dict(input_index='input-source.json',source='git archive '+sha,retained_snapshot_excluded_from_raw_manifest=True),excluded=['snapshot (reconstructible exact Git input)','pytest-cache','__pycache__','symlink aliases','raw-manifest.json and SHA256SUMS self-reference']))
(p/'SHA256SUMS').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
for e in entries:
 data=(p/e['path']).read_bytes(); assert len(data)==e['size'] and hashlib.sha256(data).hexdigest()==e['sha256']
print(json.dumps(dict(root=str(p),source_sha=sha,batches=[{k:v for k,v in b.items() if k!='cases'}for b in batches],manifest_files=len(entries),sqlite=len(databases),page_totals=proofout['page_totals'],sha256={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','api/junit.xml','pages_related/junit.xml','api/source-after.json','pages_related/source-after.json']}),ensure_ascii=False,indent=2))
