import pathlib,json,hashlib,xml.etree.ElementTree as E,sqlite3,os,collections
p=pathlib.Path(__file__).parent;sha='854e52b72d87710f18c39119ff4379f9afffc8b9'
def read(f):return json.loads(f.read_text())
def write(name,v):(p/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
batches=[];ids=[]
for b in ('api','pages_related'):
 d=p/b;suites=list(E.parse(d/'junit.xml').getroot().iter('testsuite'));cases=[]
 for c in E.parse(d/'junit.xml').getroot().iter('testcase'):
  assert not any(n.tag in('failure','error','skipped')for n in c)
  cases.append(dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0'))));ids.append(c.get('classname')+'::'+c.get('name'))
 write(b+'/collected.json',dict(provenance='Derived original JUnit; no extra collection or test execution',cases=cases))
 before=read(d/'source-before.json');after=read(d/'source-after.json');terminal=read(d/'terminal.json');assert before==after and after['equals_git_input'] and terminal['returncode']==0
 batches.append(dict(batch=b,tests=len(cases),returncode=0,failures=0,errors=0,skipped=0,junit_seconds=sum(float(s.get('time'))for s in suites),wall_seconds=terminal['wall_seconds'],source_input_count=len(after['inputs']),source_unchanged=True,cases=cases))
assert len(ids)==len(set(ids))==21
write('union.json',dict(source_sha=sha,unique_nodes=21,overlap=0,new_api=14,new_page=3,direct_legacy=4,additional_unique_over_author=0,nodeids=ids))
pages=[]
for f in sorted((p/'pages_related/data').rglob('page-result.json')):
 o=read(f);assert o['status']=='PASS'
 for a in o['assets']:
  path=p/'snapshot/src/sim2act/web'/(a['path'].lstrip('/')or'index.html');assert hashlib.sha256(path.read_bytes()).hexdigest()==a['sha256']
 new='rid'in o;req=o['requests'];worker=read(f.parent/'page-worker-proof.json')
 owners=[r for r in req if r['method']=='POST'and r['path'].endswith('/csv-owner-review-requests')]
 pages.append(dict(path=f.relative_to(p).as_posix(),kind='new_csv_owner'if new else'direct_legacy_pb_sum',case=o['case'],check_count=len(o['checks']),checks=o['checks'],requests=len(req),actual_api_replies=sum('status'in r for r in req),post_count=sum(r['method']=='POST'for r in req),assets=o['assets'],owner_commands=[dict(command=r['body']['command'],status=r.get('status'),request_key=r['body']['request_key'],delivery=r.get('delivery'))for r in owners],run_id=o.get('rid'),new_store_worker_runs=[dict(id=r['id'],status=r['status'],result_version=r.get('result_version'))for r in worker['worker_results'if new else'worker_runs']],grant_revocation='Controlled SQL fixture update, not an authorization API/UI action'if new and o['case']=='deliver'else'NONE'))
newpages=[x for x in pages if x['kind']=='new_csv_owner'];assert len(newpages)==3
sql=[]
for f in sorted((p/'api/data').rglob('scope-sql.json')):
 statements=read(f);sql.append(dict(path=f.relative_to(p).as_posix(),statement_count=len(statements),no_full_run_result_owner_payload_typed_data=not any('runs.result'in s or'csv_owner_records.payload'in s or'internal_instance_data.data'in s for s in statements)))
dbs=[]
for b in('api','pages_related'):
 for f in sorted((p/b/'data').rglob('*.db')):
  c=sqlite3.connect(f.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
  names=[r[0]for r in c.execute("select name from sqlite_master where type='table' order by name")];counts={n:c.execute('select count(*) from "'+n.replace('"','""')+'"').fetchone()[0]for n in names}
  ledgers={t:[dict(r)for r in c.execute('select run_id,sequence,kind,status,request_key from '+t+' order by run_id,sequence')]for t in('csv_owner_records','ordinary_owner_records','natural_owner_records')}
  dbs.append(dict(path=f.relative_to(p).as_posix(),counts=counts,run_headers=[dict(r)for r in c.execute('select id,status,version,principal_id,project_id,runtime_id from runs order by id')],ledgers=ledgers,attempt_ledger_rows=counts.get('attempts'),provider_scope='Attempt rows are not globally instrumented provider invocation counts'))
  c.close()
assert len(dbs)==21
summary=dict(new_page_checks=sum(x['check_count']for x in newpages),new_page_actual_api_replies=sum(x['actual_api_replies']for x in newpages),new_page_assets=sum(len(x['assets'])for x in newpages),new_page_posts=sum(x['post_count']for x in newpages),new_page_cold_store_workers=sum(len(x['new_store_worker_runs'])for x in newpages),new_page_visible_declaration_revoke_posts=sum(x['command']=='REVOKE'for q in newpages for x in q['owner_commands']),new_page_sql_grant_revocations=1,real_model_requests=0)
write('proof.json',dict(source_sha=sha,batches=batches,unique_nodes=21,overlap=0,input_count=598,input_count_breakdown=dict(src=122,tests=467,schemas=7,pyproject=1,reconstructible_gold=1),source_unchanged=True,pages=pages,new_page_summary=summary,raw_sql_traces=sql,sqlite=dbs,legacy_component=read(next((p/'pages_related/data').rglob('results.json')))))
write('review.json',dict(verdict='SUPERSEDED_COVERAGE_BLOCK',source_sha=sha,actual_result='21 PASS / 0 FAIL / 0 ERROR / 0 SKIP; both RC0; dynamic evidence preserved at its actual SHA',execution_unique=21,new_api=14,new_page=3,direct_legacy=4,automatic_retries=0,production_static_block_open=False,coverage_findings=[dict(node='test_current_authority_result_expiry_seal_and_metadata_stop[grant_redirect]',finding='Old fixture revokes every app-runtime Grant, then creates spare through project Save policy. Spare lacks app-runtime read/aggregate authorization, so the old refs-only gate also denies; this does not demonstrate redirect to another still-authorized resource.'),dict(nodes=['test_current_authority_result_expiry_seal_and_metadata_stop[receipt_bool]','test_current_authority_result_expiry_seal_and_metadata_stop[receipt_float]'],finding='Receipt mutation occurs after PREPARE. Previous loose equality can still reject DECIDE/read via changed whole context fingerprint; this does not distinguish the first-PREPARE raw-type bug.')],final_admission='Pending exact test-only tightening of these existing three parameters and new-SHA bounded rerun; other18 may be carried only after byte/path equality verification, never re-signed as executed at new SHA.',static_review=['All eight implementation findings closed in frozen source: union scalar authorization before Run/ledger body; unsupported DAG opt-in rejected before dispatch; workspace fresh read; optional module compatibility; unsent checking cleanup; continuous column consent invalidation; history and instance cache redaction; canonical fingerprint comparison of raw JSON evidence.','Prospective consent is part of request hash, accepted binding/job fingerprint and independent CSV_REVIEW_FROZEN event. Legacy coherent rehash without independently recorded marker cannot become a prospectively reviewable Run.','CSV declaration uses independent per-Run csv_owner_records/seals and existing shared ledger submit core. Declaration writes do not alter Run result/context, resources, Grant/principal or source MD acceptance.','Same Run Release/revision/input/material/hash/typed output/version/operation+intent+receipt and current user/runtime authority are checked before prepare/decision and again before commit. Human acceptance is separate from SUCCEEDED/independent sum PASS.'],limitations=['New17 CSV nodes use NoModel. The ordinary and natural human-review direct legacy nodes use synthetic Mock/Replay/MockTransport. No global provider spy was added; no real model traffic.','New pages use full served ASGI RPC and JSDOM, not native browser. setInterval is disabled; no process restart, PG, Windows, native browser, CI, deployment, publication or real human semantic verification.','New page material permission revocation is a controlled fixture SQL update; declaration REVOKE itself is an actual visible API POST. Do not conflate the two.','Fixture resource/app/Release creation precedes declaration no-authority snapshots and uses existing policies. New declarations themselves append only CSV ledger/seals.','Old P-B deliver regression does not select new CSV opt-in and its PENDING-or-human area assertion is not evidence that its legacy Run can be declared.','No retired-source injection, old long matrices, optional Ruff/mypy/node commands, or migration probe executed.'],raw_directory=str(p),raw_sqlite_count=21,raw_page_json_count=4,input_provenance='Exact Git archive plus same-SHA gold fixture; 597 src/tests/schemas/pyproject + gold1. Source snapshots are reconstructible inputs and excluded from output manifest.'))
write('packaging-note.json',dict(test_execution_affected=False,source_affected=False,note='A source-after metadata one-off script initially had an unclosed print parenthesis and failed at compile time before running or writing files; corrected metadata capture succeeded. No pytest rerun.',original_error="SyntaxError: '(' was never closed"))
entries=[]
for root,dirs,files in os.walk(p,followlinks=False):
 dirs[:]=[d for d in dirs if d not in('snapshot','pytest-cache','__pycache__')and not(pathlib.Path(root)/d).is_symlink()]
 for n in sorted(files):
  f=pathlib.Path(root)/n
  if f.is_symlink()or n in('raw-manifest.json','SHA256SUMS'):continue
  data=f.read_bytes();rel=f.relative_to(p).as_posix();entries.append(dict(path=rel,size=len(data),sha256=hashlib.sha256(data).hexdigest(),kind='runtime_original'if'/data/'in rel or n in('pytest.log','junit.xml','terminal.json','command.json')else'derived_or_reconstructible_input_metadata'))
entries.sort(key=lambda x:x['path']);write('raw-manifest.json',dict(source_sha=sha,entries=entries,total_files=len(entries),runtime_outputs_retained=True,excluded=['Reconstructible exact Git snapshot','pytest-cache','__pycache__','symlink aliases','Manifest/sums self-reference']))
(p/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n'for x in entries))
for x in entries:
 data=(p/x['path']).read_bytes();assert len(data)==x['size']and hashlib.sha256(data).hexdigest()==x['sha256']
print(json.dumps(dict(root=str(p),verdict='SUPERSEDED_COVERAGE_BLOCK',batches=[{k:v for k,v in b.items()if k!='cases'}for b in batches],page_summary=summary,manifest_files=len(entries),sha256={n:hashlib.sha256((p/n).read_bytes()).hexdigest()for n in['review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','api/junit.xml','pages_related/junit.xml']}),indent=2))
