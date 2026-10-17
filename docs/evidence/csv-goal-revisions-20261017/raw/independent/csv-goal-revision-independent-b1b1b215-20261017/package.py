import collections, hashlib, json, os, sqlite3, xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
SHA='b1b1b2159b850ac0a058e2a6cc1e86b275579f79'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
root=ET.parse(R/'junit.xml').getroot();s=root.find('testsuite') if root.tag!='testsuite' else root
cases=list(root.iter('testcase'))
counts={k:int(s.get(k,'0')) for k in ('tests','failures','errors','skipped')}
counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
collected=[]
for c in cases:
 outcome='FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS'
 collected.append(dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0')),outcome=outcome))
save('collected.json',collected)
before=json.loads((R/'source-before.json').read_text());after=json.loads((R/'source-after.json').read_text())
shared=json.loads((R/'shared-source-after.json').read_text())
assert before['inputs']==after['inputs'] and after['equal_to_before'] and after['all_match_git']
breakdown=dict(collections.Counter(i['path'].split('/')[0] for i in before['inputs']))
pages=[]
for p in sorted((R/'data').rglob('page-result.json')):
 d=json.loads(p.read_text());info=p.parent/'info.json';info=json.loads(info.read_text()) if info.exists() else {}
 assets=[]
 for a in d.get('assets',[]):
  path=a.get('path',a.get('url',''))
  f=R/'snapshot/src/sim2act/web'/(path.split('?',1)[0].lstrip('/') or 'index.html')
  assets.append(dict(path=path,sha256=a['sha256'],matches_frozen_input=f.is_file() and digest(f)==a['sha256']))
 replies=[q for q in d.get('requests',[]) if isinstance(q.get('status'),int)]
 pages.append(dict(path=p.relative_to(R).as_posix(),case=info.get('case'),status=d.get('status'),checks=d.get('checks',[]),check_count=len(d.get('checks',[])),api_issued=len(d.get('requests',[])),actual_replies=len(replies),status_counts=dict(collections.Counter(str(q['status']) for q in replies)),assets=assets))
assert all(a['matches_frozen_input'] for page in pages for a in page['assets'])
save('page-summary.json',pages)
dbs=[]
for p in sorted((R/'data').rglob('*.db')):
 if p.is_symlink():continue
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
 try:
  tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  item=dict(path=p.relative_to(R).as_posix(),tables={t:c.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables})
  if 'runs' in tables:item['run_statuses']=dict(c.execute('SELECT status,count(*) FROM runs GROUP BY status'))
  dbs.append(item)
 finally:c.close()
save('database-summary.json',dbs)
terminal=json.loads((R/'terminal.json').read_text());junit=float(s.get('time','0'))
outputs={}
for name in ('actual-delivery.json','actual-browser-delivery.json','actual-http.json','node.stderr'):
 outputs[name]=[p.relative_to(R).as_posix() for p in sorted((R/'data').rglob(name)) if not p.is_symlink()]
summary=dict(source_sha=SHA,counts=counts,junit_seconds=junit,terminal=terminal,input_count=before['count'],input_breakdown=breakdown,page_count=len(pages),page_checks=sum(p['check_count'] for p in pages),page_api_issued=sum(p['api_issued'] for p in pages),page_actual_replies=sum(p['actual_replies'] for p in pages),served_asset_records=sum(len(p['assets']) for p in pages),all_served_asset_hashes_match_frozen_input=True,database_files=len(dbs),output_files=outputs)
save('summary.json',summary)
passed=counts==dict(tests=16,failures=0,errors=0,skipped=0,passed=16) and terminal['returncode']==0
proof=dict(source_sha=SHA,actual_execution_nodes=len(cases),unique_nodes=len({(c['classname'],c['name']) for c in collected}),automatic_retries=0,returncode=terminal['returncode'],junit_seconds=junit,input_count=before['count'],input_breakdown=breakdown,extra_input='docs/evidence/bounded-agent-offline-20261006/independent-gold.json',snapshot_all_input_git_blobs_and_sha256_equal_before_after=True,shared_source_after_head=shared['head'],shared_source_after_equals_frozen=shared['equal_to_frozen'],actual_scope='12 new (8 API + 4 ASGI/JSDOM pages) and 4 directly related existing nodes; independent duplicate of author selection, zero additional unique over author.',page_summary='page-summary.json',raw_outputs=outputs,sql_trace_scope='SQL positive-control and denied-before-private-SELECT assertions ran inside two API tests; tests do not persist a separate SQL-statement sidecar. The original frozen tests, actual HTTP arrays, SQLite state, and terminal results are preserved.',downloads='No Blob/download path is exercised by this finite structured-sum revision slice; actual-delivery files are JSON server/SQL proofs.',pending_targeted_oracle='The current CHECK-directory omission assertion examines an unrefreshed list. It does not establish filtering against an actual post-CHECK instance-list response. Parent plans a test-only targeted deliver refinement; current original execution is preserved, not final admission for that claim.')
save('proof.json',proof)
review=dict(verdict='EXECUTION_PASS_PENDING_TARGETED_ORACLE' if passed else 'BLOCKED_ACTUAL_FAILURE',source_sha=SHA,execution=counts,junit_seconds=junit,static_review=dict(production_blockers_remaining=[],closed_findings=['Scalar owned instance lookup prevents source_gate/current Release recursion after adoption.','Current-head material-ID union is authorized before full Goal/proposal bodies; historical reads use frozen versions.','Independent CHECK request/seal, binding purpose, and frozen event pin its instance and exact Run/AppRun; business enqueue/switch cannot reuse it.','Immutable Release SOURCE and request-key AppRun Release linkage prevent marker deletion from downgrading a revised job.','Release listing selects owned app-filtered IDs before protected read; approval SOURCE indexes and seals are verified.','proposal_tx reads only scalar existence metadata, checks kind and seal plus independent JOB/event/approval origins, and emits proven rejection only after completed rollback.','Same app/runtime, original candidate/generation and base Release remain unchanged; effective Goal/column changes are independently frozen, and original business-instance adoption uses existing CAS.','UI separate consent, original-key GET-only unknown recovery, current controller/identity/project/workspace/instance fences and late-entry notification remain bounded.'],finite_scope='Only one explicit same-material next Goal version and amount-to-quantity finite column-definition revision. This does not interpret arbitrary natural-language goals or provide unrestricted edits.',coverage_gap=dict(path='tests/csv_goal_revision.cjs:66',finding='CHECK omission is asserted against pre-CHECK directory DOM without a new list read.',classification='test oracle gap; role-based filter exists statically; no demonstrated product failure.',status='Parent accepted targeted test-only deliver follow-up; current batch unmodified.')),dynamic_scope='Actual existing NoModel Worker with new Store objects over SQLite; exact structured sum and frozen Goal v2, separate Release confirmation and original-instance adoption, old amount result preserved, new result human PENDING. Synthetic old human decisions are simulated declarations, not real human semantic acceptance.',authority_scope='No new executor/runtime/Grant type or rows from the finite revision path; existing fixture creation policies remain. Current authority is rechecked; controlled SQL corruption/revocation cases are synthetic, not production UI authority changes.',model_scope='Selected new and related paths use NoModel deterministic registered tools; no real provider calls. No generalized language-quality or semantic-completion claim.',not_run=['PG','native browser','Windows','CI','deployment','process restart','real model/provider','real human semantic acceptance','cross-platform-cap historical reads','extra recovery or failure matrix','fresh post-CHECK directory omission proof (targeted follow-up pending)'],baseline_note='No baseline test or old historical matrix was rerun independently in this batch.',evidence_root=str(R),source_exclusions='Reconstructible snapshot input bytes and dependency/cache symlinks are excluded from raw manifest; every tracked input Git blob, SHA256 and size is retained before and after.')
save('review.json',review)
entries=[]
for folder,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[n for n in dirs if n not in ('snapshot','pytest-cache','__pycache__') and not (Path(folder)/n).is_symlink()]
 for name in files:
  p=Path(folder)/name
  if p.is_symlink() or p.suffix=='.pyc' or name in ('raw-manifest.json','SHA256SUMS'):continue
  rel=p.relative_to(R).as_posix()
  entries.append(dict(path=rel,bytes=p.stat().st_size,sha256=digest(p),classification='original-test-output' if rel.startswith('data/') or name in ('pytest.log','junit.xml','terminal.json') else 'original-independent-provenance-or-review'))
entries.sort(key=lambda e:e['path'])
save('raw-manifest.json',dict(source_sha=SHA,count=len(entries),excluded=['reconstructible Git snapshot','dependency symlinks','pytest-cache','pycache','manifest/sums self-reference'],files=entries))
(R/'SHA256SUMS').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
assert all((R/e['path']).stat().st_size==e['bytes'] and digest(R/e['path'])==e['sha256'] for e in entries)
print(json.dumps(dict(ready=True,root=str(R),verdict=review['verdict'],counts=counts,junit_seconds=junit,manifest_entries=len(entries),source_inputs=before['count'],page_checks=summary['page_checks'],page_api=summary['page_actual_replies'],assets=summary['served_asset_records'],hashes={n:digest(R/n) for n in ('review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','junit.xml','summary.json')}),ensure_ascii=False,indent=2))
