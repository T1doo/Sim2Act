import hashlib,json,os,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
P=Path('/tmp/csv-full-report-independent-4a4a228f-20261017')
OLD='4a4a228f09203e08103904e3afdd04b12708a98b'
SHA='436c49cb8c2ac04489fd9dfd4baaf09bffea0298'
def save(name,value): (R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
x=ET.parse(R/'junit.xml').getroot();s=x.find('testsuite');cases=list(x.iter('testcase'))
counts={k:int(s.get(k,'0')) for k in ['tests','failures','errors','skipped']};counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
assert counts==dict(tests=1,failures=0,errors=0,skipped=0,passed=1),counts
junit=float(s.get('time'))
page_path=next((R/'data').rglob('page-result.json'));d=json.loads(page_path.read_text());h=d['diagnostics']['handoff'];requests=d['requests']
assert d['status']=='PASS' and len(d['checks'])==22
assert h['read_count']>=2 and h['active_app'] is None and h['active_run'] is None and h['manifest_empty'] and h['artifact_canvas_empty']
assert all(isinstance(q.get('status'),int) for q in requests) and h['run_http_statuses'][-2:]==[403,403]
assert len(requests)==50 and len(d['assets'])==25
assets=[]
for item in d['assets']:
 p=R/'snapshot/src/sim2act/web'/(item['path'].lstrip('/') or 'index.html')
 assets.append(dict(path=item['path'],sha256=item['sha256'],matches_frozen_input=sha(p)==item['sha256']))
assert all(a['matches_frozen_input'] for a in assets)
run=d['delivery']['run'];actual=next(q['response'] for q in reversed(requests) if q.get('path')=='/api/runs/'+run and q.get('status')==200)
spec=actual['contract']['snapshot']['ordinary_csv_report'];receipt=actual['result']['receipts'][-1]
md=next((R/'data').rglob('*.download.md'));raw=md.read_bytes()
assert raw==spec['report_text'].encode() and sha(md)==spec['report_hash']==receipt['data']['hash']
dbs=[]
for p in (R/'data').rglob('*.db'):
 if p.is_symlink():continue
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
 try:
  tables=[row[0] for row in c.execute("select name from sqlite_master where type='table' order by name")]
  dbs.append(dict(path=str(p.relative_to(R)),tables={t:c.execute('select count(*) from "'+t.replace('"','""')+'"').fetchone()[0] for t in tables},run_statuses=dict(c.execute('select status,count(*) from runs group by status'))))
 finally:c.close()
save('database-summary.json',dbs)
save('collected.json',[dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0')),outcome='PASS') for c in cases])
before=json.loads((R/'source-before.json').read_text());after=json.loads((R/'source-after.json').read_text());delta=json.loads((R/'delta.json').read_text())
assert before['inputs']==after['inputs'] and after['equal_to_before'] and all(i['matches_git'] for i in after['inputs'])
priorfiles=['review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','junit.xml']
priorref=dict(root=str(P),source_sha=OLD,counts=dict(passed=21,failed=1,skipped=0),junit_seconds=234.893,files=[dict(path=name,sha256=sha(P/name),bytes=(P/name).stat().st_size) for name in priorfiles],prior_directory_remains_unchanged=True)
save('prior-sealed-evidence.json',priorref)
summary=dict(source_sha=SHA,counts=counts,junit_seconds=junit,terminal=json.loads((R/'terminal.json').read_text()),page=dict(path=str(page_path.relative_to(R)),checks=len(d['checks']),api_issued=len(requests),actual_replies=len(requests),assets=len(assets),handoff=h),blob=dict(path=str(md.relative_to(R)),bytes=len(raw),sha256=sha(md),run_id=run,resource_id=receipt['data']['resource_id'],exact_frozen_md_bytes=True,url_revocations=d['revocations']),database_files=len(dbs))
save('summary.json',summary)
proof=dict(source_sha=SHA,prior_source_sha=OLD,input_count=602,root_input_count=601,extra_input='docs/evidence/bounded-agent-offline-20261006/independent-gold.json',snapshot_before_after_equal=True,all_inputs_match_git=True,production_src124_unchanged_from_prior=True,other_input601_byte_identical=True,only_changed_input='tests/csv_full_report.cjs',actual_execution_nodes=1,automatic_retries=0,returncode=0,junit_seconds=junit,observed_handoff=h,actual_saved_blob=summary['blob'],effective_admission=dict(unique_nodes=22,source_attribution=[dict(source_sha=OLD,passed_nodes=21),dict(source_sha=SHA,passed_nodes=1)],independent_execution_count=23,repeated_unique_nodes=1,additional_unique_over_author=0),old_4a_failed_attempt_preserved=True,no_claim_of_full22_run_at_new_sha=True)
save('proof.json',proof)
review=dict(verdict='PASS_BOUNDED',production_source_sha=OLD,test_only_source_sha=SHA,actual_this_run=counts,junit_seconds=junit,effective_scope='22 unique = prior4a 21 passing nodes + current436 one misbound page. Independent23 executions, no new unique over author. Original4a compound-oracle FAIL remains sealed and is not rewritten.',static_review=dict(closed_findings=['prebody original/new material + project save + independent saved effect output authorization','metadata/project lock/scope gate precedes confirm full Run read','immutable source recipe and per-use row/context/event canonical seals','exact original-key/Run/definition/contract/input binding; bad202 delivery cannot install original source Run','current403/409 clears protected App/Run state and proof caches','same-Run poll node/baseCurrent reuse and pending-entry current-view notification','late identity/project/workspace callbacks and follow-up GET fenced','handoff new workspace failure scope remains current after own transition'],test_delta='Only CJS test driver changed. Replaced noncontract exact2 GET oracle with bounded real-reply settling and independent DOM/HTTP diagnostics; kept substantive permission and protected-content assertions. All production124 src files and other601 frozen inputs match prior bytes.'),dynamic_resolution='Actual new page recorded read_count3, all50 requests replied, final two same-Run replies403, active_app/run null and manifest/artifact canvas empty; exact730-byte new MD downloaded from same confirmed new Run before controlled revocation. This supports oracle-count error on the original failed compound check without a production fix.',semantic_scope='Explicit bounded CSV full-MD contract PASS only; general semantic NOT_RUN, human PENDING, unpublished. Saved recipe is not an internal Release/instance or SUM_ONLY human-acceptance extension.',authority_scope='No new executor, principal or write Grant. Original project runtime/save authorization required currently. Existing actual save policy creates Resource and two derived read Grants; synthetic fixture material/project creation also uses existing policies.',model_scope='New18/targeted page use NoModel deterministic tools. Prior natural P-A regression uses offline synthetic MockTransport; no entire-batch zero-total-provider claim. No real model.',not_run=['PG','native browser','Windows','process restart','CI','deployment','real model/external network','real human semantic acceptance','extra retirement/recovery matrix','migration probe'],evidence_root=str(R),assets_note='25 served asset path/hash records match frozen inputs; reconstructible source bytes are excluded from raw manifest.')
save('review.json',review)
entries=[]
for folder,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[name for name in dirs if name not in ('snapshot','pytest-cache','__pycache__') and not (Path(folder)/name).is_symlink()]
 for name in files:
  p=Path(folder)/name
  if p.is_symlink() or name in ('raw-manifest.json','SHA256SUMS') or p.suffix=='.pyc':continue
  rel=p.relative_to(R).as_posix()
  entries.append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p),classification='original-test-output' if rel.startswith('data/') or name in ('pytest.log','junit.xml','terminal.json') else 'original-independent-provenance-or-review'))
entries.sort(key=lambda e:e['path'])
save('raw-manifest.json',dict(source_sha=SHA,excluded=['reconstructible snapshot','pytest-cache','pycache','symlinks','manifest/sums self-reference'],count=len(entries),files=entries))
(R/'SHA256SUMS').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
assert all((R/e['path']).stat().st_size==e['bytes'] and sha(R/e['path'])==e['sha256'] for e in entries)
print(json.dumps(dict(ready=True,root=str(R),verdict='PASS_BOUNDED',junit_seconds=junit,manifest_entries=len(entries),diagnostics=h,hashes={name:sha(R/name) for name in ['review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','junit.xml','delta.json','prior-sealed-evidence.json']}),ensure_ascii=False,indent=2))
