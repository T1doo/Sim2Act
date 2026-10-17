import hashlib,json,os,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
SHA='4a4a228f09203e08103904e3afdd04b12708a98b'
def save(name,value): (R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
x=ET.parse(R/'junit.xml').getroot(); suites=list(x.iter('testsuite')); cases=list(x.iter('testcase'))
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','failures','errors','skipped']}
counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
junit_seconds=sum(float(s.get('time','0')) for s in suites)
collected=[dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0')),outcome='FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS') for c in cases]
save('collected.json',collected)
assert counts==dict(tests=22,failures=1,errors=0,skipped=0,passed=21),counts
pages=[]
for p in sorted((R/'data').rglob('page-result.json')):
 d=json.loads(p.read_text());info=json.loads((p.parent/'info.json').read_text());req=d.get('requests',[])
 asset_match=[]
 for a in d.get('assets',[]):
  source=R/'snapshot/src/sim2act/web'/(a['path'].lstrip('/') or 'index.html')
  asset_match.append(source.exists() and sha(source)==a['sha256'])
 pages.append(dict(path=str(p.relative_to(R)),case=info['case'],status=d['status'],checks=len(d.get('checks',[])),requests=len(req),actual_replies=sum(isinstance(q.get('status'),int) for q in req),pending_replies=sum(not isinstance(q.get('status'),int) for q in req),post_requests=sum(q.get('method')=='POST' for q in req),assets=len(d.get('assets',[])),all_assets_match_frozen_git=all(asset_match),error=d.get('error')))
dbs=[]
for folder,dirs,files in os.walk(R/'data',followlinks=False):
 dirs[:]=[name for name in dirs if not (Path(folder)/name).is_symlink()]
 for name in files:
  p=Path(folder)/name
  if p.is_symlink() or p.suffix not in ('.db','.sqlite','.sqlite3'):continue
  c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
  try:
   tables=[row[0] for row in c.execute("select name from sqlite_master where type='table' order by name")]
   counts_by_table={t:c.execute('select count(*) from "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
   statuses=dict(c.execute('select status,count(*) from runs group by status')) if 'runs' in tables else {}
   dbs.append(dict(path=str(p.relative_to(R)),tables=counts_by_table,run_statuses=statuses))
  finally:c.close()
save('database-summary.json',dbs)
md=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted((R/'data').rglob('*.md')) if p.is_file() and not p.is_symlink()]
summary=dict(source_sha=SHA,counts=counts,junit_seconds=junit_seconds,terminal=json.loads((R/'terminal.json').read_text()),pages=pages,original_md_files=md,sqlite_files=len(dbs))
save('summary.json',summary)
before=json.loads((R/'source-before.json').read_text());after=json.loads((R/'source-after.json').read_text());shared=json.loads((R/'shared-source-after.json').read_text())
assert before['inputs']==after['inputs'] and after['equal_to_before'] and shared['equal_to_frozen']
proof=dict(source_sha=SHA,input_count=602,input_scope='tracked src/tests/schemas/pyproject.toml plus same-SHA independent-gold.json',snapshot_before_after_equal=True,all_inputs_match_git=True,shared_worktree_before_after_equal_at_recorded_boundary=True,actual_nodes=22,unique_nodes=22,automatic_retries=0,returncode=1,junit_seconds=junit_seconds,counts=counts,global_node_path='/workspace/Sim2Act/scripts/engineering-ci/node_modules',old_application_use='ACTUAL_PASS_NOT_SKIP',original_failed_page='data/test_visible_complete_report_d2/page-result.json',failed_predicate='secondRunRevoke.count === 2 AND protected App/Run DOM cleared',failed_page_observation='21 earlier checks passed; three final same-Run GETs observed, one not settled at assertion. Original failed JSON does not isolate all DOM subvalues. This run cannot establish product clearance or its failure from the compound predicate alone.',no_test_rerun=True)
save('proof.json',proof)
review=dict(verdict='NOT_ADMITTED_PENDING_TARGETED_ORACLE_CORRECTION',source_sha=SHA,static_verdict='NO_REMAINING_IDENTIFIED_PRODUCT_BLOCK_AT_FROZEN_SOURCE',dynamic=counts,junit_seconds=junit_seconds,closed_static_findings=['current 403/409 clears protected Run/App state and extraction proof cache','new saved MD independent local_effects ID authorized before full Run body; corrupted receipt refs cannot bypass','confirm uses metadata then current scope gate before full Run read','POST hint verified by original-key read; open/history verify exact workflow/definition/Run/contract/source request bindings','same-Run background extraction reuses node and refreshes baseCurrent','follow-up GET checks current view before using global identity; stale acceptance retains original UNKNOWN key','canonical fingerprints distinguish bool/float from integer in binding/event seals','handoff workspace has its own failure fence; current same-entry pending view receives settle notification'],failure_limit='The failed final oracle requires exactly two reads, while workspace resume plus explicit read may produce three. No production success claimed; retain full failure and validate a corrected diagnostic/settle predicate at a new test-only SHA.',scope=['18 new nodes = 13 API + 5 full served-page JSDOM; four direct regressions','new path uses deterministic original three tools/NoModel; legacy natural P-A regression uses offline synthetic MockTransport, so entire batch is not described as zero total model/provider calls','complete limited CSV contract PASS stays separate from general semantic NOT_RUN, human PENDING and publication disabled','saving/preparing recipe creates no principal or new save authority; actual artifact save retains existing two derived read Grants','ASGI/TestClient + SQLite + JSDOM; same-process Worker objects, not native browser or process restart'],not_run=['PG','native browser','Windows','real model/network calls','CI','deployment','real human semantic acceptance','extra retirement or historical recovery matrix','migration probe'],evidence_root=str(R),raw_assets_note='Page JSON preserves served asset path/hash, checked against frozen Git inputs; asset response bodies are reconstructible inputs, not separately claimed as raw response files.')
save('review.json',review)
entries=[]
for folder,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[name for name in dirs if name not in ('snapshot','pytest-cache','__pycache__') and not (Path(folder)/name).is_symlink()]
 for name in files:
  p=Path(folder)/name
  if p.is_symlink() or name in ('raw-manifest.json','SHA256SUMS') or p.suffix=='.pyc':continue
  rel=p.relative_to(R).as_posix();kind='original-test-output' if rel.startswith('data/') or name in ('pytest.log','junit.xml','terminal.json') else 'original-independent-provenance-or-review'
  entries.append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p),classification=kind))
entries.sort(key=lambda e:e['path'])
save('raw-manifest.json',dict(source_sha=SHA,excluded=['snapshot (reconstructible frozen Git inputs and read-only dependency symlink)','pytest-cache','pycache','symlinks','manifest/sums self-reference'],files=entries,count=len(entries)))
(R/'SHA256SUMS').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
assert all((R/e['path']).stat().st_size==e['bytes'] and sha(R/e['path'])==e['sha256'] for e in entries)
print(json.dumps(dict(ready=True,root=str(R),counts=counts,junit_seconds=junit_seconds,manifest_entries=len(entries),sqlite_files=len(dbs),pages=pages,md_files=len(md),hashes={name:sha(R/name) for name in ['review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','junit.xml']}),ensure_ascii=False,indent=2))
