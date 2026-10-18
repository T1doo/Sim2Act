import datetime, hashlib, json, pathlib, sqlite3, subprocess, xml.etree.ElementTree as ET
repo=pathlib.Path('/workspace/Sim2Act')
out=pathlib.Path('/workspace/local-record-ui-independent-review-20261018')
root=pathlib.Path('/workspace/local-record-state-evidence-20261018')
sha='d5eadc708ee2968bb574ec66e335c05451f66cf7'
ui_sha='a38c33f7496dca3da079d59bab16f13b5c283d1e'
test_sha='81ad223bf72fb6e15af03ef6aca87af70e9bf4f8'
files={}
for name in ['src/sim2act/web/local-records.js','src/sim2act/web/app.js','src/sim2act/web/use.js','src/sim2act/web/index.html','src/sim2act/local_record_apps.py','tests/test_local_record_apps_ui.py','tests/local_record_apps_ui.cjs']:
 raw=(repo/name).read_bytes(); frozen=subprocess.check_output(['git','show',sha+':'+name],cwd=repo)
 assert raw==frozen,name
 files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'current_equals_final_commit':True}
 if name.startswith('src/sim2act/web/'):
  older=subprocess.check_output(['git','show',ui_sha+':'+name],cwd=repo)
  assert raw==older
  files[name]['equal_product_a38_UI_bytes']=True
suites=[]
for label in ['ui-final','ui-d5eadc70']:
 xml=root/(label+'.xml')
 suite=next(ET.parse(xml).getroot().iter('testsuite'))
 assert suite.attrib['tests']=='3' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0' and suite.attrib['skipped']=='0'
 cases=[]
 for case in suite.findall('testcase'):
  assert case.find('failure') is None and case.find('error') is None and case.find('skipped') is None
  cases.append({'name':case.attrib['name'],'seconds':case.attrib['time'],'outcome':'PASS'})
 scenes=[]
 for folder in sorted((root/label).iterdir()):
  if not folder.is_dir() or folder.is_symlink():continue
  page=json.loads((folder/'page-result.json').read_text()); summary=json.loads((folder/'run-summary.json').read_text())
  assert page['status']==summary['status']=='PASS' and summary['node_exit_code']==0
  before=json.loads((folder/'source-before.json').read_text()); after=json.loads((folder/'source-after.json').read_text())
  assert before==after and json.loads((folder/'source-changes.json').read_text())=={}
  if label=='ui-d5eadc70':
   for name,item in before.items():
    raw=(repo/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256'],name
    assert raw==subprocess.check_output(['git','show',sha+':'+name],cwd=repo),name
  for asset in page['static_resource_loads']:
   raw=(repo/'src/sim2act/web'/(asset['path'].lstrip('/') or 'index.html')).read_bytes()
   assert asset['status']==200 and hashlib.sha256(raw).hexdigest()==asset['sha256']
  scene={'scenario':page['scenario'],'classification':page['classification'],'node_exit_code':summary['node_exit_code'],'checks':len(page['checks']),'page_HTTP_actions':len(page['actions']),'page_POSTs':sum(a['method']=='POST' for a in page['actions']),'served_assets_observed':len(page['static_resource_loads']),'boots':page['boots'],'page_worker_calls':summary['page_worker_calls'],'fixture_worker_calls':summary['fixture_worker_calls'],'source_before_after_same':True,'source_manifest_files':len(before),'raw_folder':str(folder)}
  if page['scenario']=='revocation':
   p=json.loads((folder/'actual-revocation-proof.json').read_text())
   assert p['changed_tables']==['grants'] and p['only_exact_known_grant_changed'] and p['all_other_rows_unchanged'] and p['original_run_rows_unchanged']
   assert len(p['fixture_grant_mutations'])==1 and p['page_post_count']==p['page_worker_calls']==0
   denied=[a for a in page['actions'] if a['status']==403]
   assert len(denied)==2 and all(a['method']=='GET' for a in denied)
   g=p['fixture_grant_mutations'][0]
   assert g['after']=={**g['before'],'revoked':True,'revision':g['before']['revision']+1}
   scene['denied_GET_paths']=[a['path'] for a in denied]
   scene['only_changed_Grant']=g
  if label=='ui-d5eadc70':
   db=folder/'fixture.db'; b=hashlib.sha256(db.read_bytes()).hexdigest()
   c=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True); c.row_factory=sqlite3.Row
   runs=[dict(r) for r in c.execute('SELECT id,status,fence,request_key FROM runs ORDER BY id')]
   claims=[dict(r) for r in c.execute("SELECT run_id,data FROM events WHERE kind='CLAIMED' ORDER BY run_id")]
   assert all(r['status']=='SUCCEEDED' and r['fence']==1 for r in runs)
   assert len(claims)==len(runs) and {r['run_id'] for r in claims}=={r['id'] for r in runs}
   assert c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==c.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0
   if page['scenario']=='revocation':
    actual=dict(c.execute('SELECT * FROM grants WHERE id=?',(scene['only_changed_Grant']['after']['id'],)).fetchone())
    actual['revoked']=bool(actual['revoked'])
    assert actual==scene['only_changed_Grant']['after']
   c.close(); a=hashlib.sha256(db.read_bytes()).hexdigest(); assert a==b
   scene['readonly_database_check']={'db_sha256':a,'file_unchanged_by_review':True,'Run_rows':runs,'claim_count':len(claims),'attempts':0,'reservations':0}
  scenes.append(scene)
 suites.append({'label':label,'seconds':suite.attrib['time'],'cases':cases,'scenes':scenes,'raw_junit':str(xml),'raw_junit_sha256':hashlib.sha256(xml.read_bytes()).hexdigest(),'raw_log':str(root/(label+'.log'))})
final=suites[1]
assert len(final['scenes'])==3 and sum(x['checks'] for x in final['scenes'])==132
proof={'review_time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'production_sha':sha,'UI_byte_source_sha':ui_sha,'test_sha':test_sha,'baseline':'5322dfd7f8c6686be29c9989d2f02fb6f54cfc28','qualification_role':'Non-author UI source reviewer, author of bounded additional revocation test draft, independent reader of root-executed final raw evidence; not an independent execution of the full UI suite.','reviewer_executed':['Python AST parse on proposed test wrapper','Node --check on proposed CJS driver','read-only source/diff/hash/evidence and SQLite metadata inspection'],'reviewer_pytest_or_worker_executions':0,'repository_writes':0,'files':files,'resolved_findings':[{'severity':'P2','title':'Prior recovery/projection/private form bodies survived current authorization/read failure','original_locations':'localRecordsRefresh catch ~240; localRecordsRecover catch ~307 before fix','fix_locations':'local-records.js localRecordsClearPrivate 177-180; Post catch 133; Delivery catch 157; Refresh catch 244; Recover catch 311','resolution':'Unified helper invalidates read/edit generation, clears projection/history/Run/preview/recovery and title/details/reason/record selector, retains exact original key and intent map. Final real revocation scene proves both 403 paths with zero page POST and original Run preservation.'}],'remaining_P1_P2':[],'bounded_static_conclusion':'No remaining definite P1/P2 found in the reviewed UI/controller and HTTP-receipt integration scope.','source_and_test_bridge':'a38 to d5 production change is Python-only local type narrowing and post-require assert; all four reviewed UI files are byte-identical. Final raw manifests are additionally checked against exact d5 Git files.','author_execution_batches':suites,'unique_final_UI_cases':3,'final_UI_check_labels':132,'not_additive':'Earlier 3PASS49.484s and final 3PASS50.03s repeat the same three cases; do not add as six unique cases or an independent re-execution.','runtime_limits':['hash-await fences reviewed statically; the HTTP navigation scene delays actual responses, not crypto.subtle.digest','No native browser/Windows/PG/real model/real semantic acceptance','Not a full non-author backend security or recovery-matrix audit','Earlier 9 API cases and pre-fix 2 UI cases are parent evidence outside this report; not independently rerun or added to final three'],'result':'LIMITED_PASS'}
(out/'final-ui-review-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
report=f'''# Local record UI: independent limited review

Production commit: `{sha}`. UI bytes are identical to `{ui_sha}`; tests were frozen at `{test_sha}`. Baseline: `5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`.

**Limited conclusion:** no remaining definite P1/P2 issue was found in the reviewed UI/controller and actual HTTP-receipt integration scope. The earlier P2 was fixed and is covered by the final real revocation scenario. This reviewer performed non-author source review, proposed the additional bounded revocation test, and independently read the root-executed raw results. It did **not** independently execute the full UI suite or any Worker.

## Finding and correction

P2: prior full original-key recovery replies contain record title/details in the recovery proof. Previously Refresh failure cleared only collection/history/Run proof while leaving that recovery body, and Recover failure only changed status. A current 403 could therefore leave revoked private record text visible.

The frozen fix is `localRecordsClearPrivate` (lines177-180), called by current Post, Delivery, Refresh and Recover error branches (lines133,157,244,311). It invalidates read/edit generations, clears current collection/history/Run/preview/recovery bodies and record form fields, and retains the exact original request key plus intent map. It does not mark a background Run failed. No repository file was changed by this reviewer.

The added third test scenario starts from exactly one genuine synthetic seed. The page first reads its successful Run and uses original-key GET to restore the body, then a closed fixture-only RPC revokes exactly its known artifact owner resource.read Grant. The real Refresh GET and original-key GET each return403. Both clear all old text/form fields, preserve key/stage, perform zero page POST and zero page Worker. Whole-database assertions allow only that known Grant's revoked/revision change; original Run rows and all other rows remain unchanged. The RPC cannot select arbitrary Grant/principal/project or resource, and is callable once only in this scenario.

## Final raw results independently read

Root final batch `ui-d5eadc70`: **3 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, JUnit {final['seconds']} seconds; all three Node processes exit0. This review did not launch that pytest process. Its three scenarios record132 check labels:

- flow-recovery:62 checks,56 page HTTP actions,10 explicit POSTs,3 page NoModel Worker calls. It creates the app, separately prepares/commits Release and creates/selects the instance, then performs CREATE A, CREATE B and SET_STATE A→DONE. One accepted receipt is deliberately lost after actual HTTP, and only explicit original-key GET recovers it. A cold page preserves old OPEN event beside current A DONE@2 and unchanged B OPEN@1.
- navigation:36 checks,60 page HTTP actions,zero page POST/Worker and one fixture seed. Controlled late actual HTTP responses are isolated across instance selection, Run deselection, original-key recovery, workspace ABA, new-app navigation, project ABA and same-account reconnect.
- revocation:34 checks,18 page HTTP actions,zero page POST/Worker and one fixture seed; the two actual GET403 paths cover the resolved P2.

All served asset hashes (54/27/27 across2/1/1 boots) match the frozen files. Every final per-case source-before/source-after manifest is unchanged and matches exact d5 Git bytes. Read-only SQLite inspection found5 distinct successful Runs across the three fixtures, each with one claim/fence1, zero attempts/reservations, and unchanged database file hashes during this review. These are synthetic NoModel engineering results, not real semantic acceptance.

The preceding root batch `ui-final` also has3PASS, JUnit49.484s on the same UI bytes. It is kept as a separate earlier phase; it is not six unique cases or an independent rerun. The d5 change from a38 is limited to Python type narrowing and an assertion after an existing rejecting guard.

## Bounded source review

`localRecordsCurrent/Fence` capture identity, connection, project, workspace/app epochs, view identity, instance selection, read and edit generations. Each POST sets its scope intent and sending/busy lock before its first hash await; every hash/HTTP await checks the captured current predicate before adoption. UNKNOWN requests retain their original key and cannot automatically POST or change key. Explicit recovery usesGET; acceptance never claims a successful business record before the same Run is read. The scene runner's double clicks demonstrate one accepted write per explicit phase.

Creation, Release approval/commit, instance creation/selection and typed preview/commit are separately reachable. New family metadata routes to its dedicated controller and does not automatically create a version or Run. Canonical event hashes and linked previous collection/record hashes are folded into the collection; the same Run's event/output/verified receipt must match that history. Original artifact.save_text output remains the real resource_id/hash, while current records are explicitly separate adapter projections. The new UI uses textContent and fixed DOM elements for names, record bodies, reasons, proof and error text; no user content is inserted as HTML.

## Remaining scope limits

The actual navigation test controls HTTP response delivery. Hash-await current checks were inspected statically; no separate held-crypto runtime probe was executed. This was not a full independent backend/lease/recovery-matrix audit. Native browser, Windows, PG, real model, real semantic acceptance and remote CI were not run. Prior API tests and earlier pre-fix UI tests retain their own execution evidence and are not counted as this final three-case result.

Raw source/result paths, hashes, per-scenario counts and read-only DB observations are recorded in `final-ui-review-proof.json`. Original author outputs remain at `/workspace/local-record-state-evidence-20261018/ui-d5eadc70{{.log,.xml,/}}` and the preceding `ui-final` paths.
'''
(out/'final-ui-review.md').write_text(report)
# No raw author artifacts are rewritten or moved by this review.
for name in ['final-ui-review.md','final-ui-review-proof.json']:
 p=out/name; print(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
print({'result':'LIMITED_PASS','remaining_P1_P2':0,'root_final_tests':3,'reviewer_full_UI_executions':0})
