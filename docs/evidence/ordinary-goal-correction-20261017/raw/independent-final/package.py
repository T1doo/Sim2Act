import datetime,hashlib,json,os,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).parent;sha='d731199a1fd6272e1a79e1c761a1461500fd5227'
def write(name,value): (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def digest(p):
 d=p.read_bytes();return dict(size=len(d),sha256=hashlib.sha256(d).hexdigest())
source=json.loads((root/'source-inputs.json').read_text());batches=[];allnodes=[]
for name,expected in [('api',23),('pages-related',14)]:
 batch=root/name;terminal=json.loads((batch/'terminal.json').read_text());before=json.loads((batch/'source-before.json').read_text());after=json.loads((batch/'source-after.json').read_text());collected=json.loads((batch/'collected.json').read_text())
 assert before['inputs']==after['inputs']==source['inputs'] and after['identical_to_before']
 xml=ET.parse(batch/'junit.xml').getroot();nodes=list(xml.iter('testcase'));keys=[str(x.get('classname'))+'::'+str(x.get('name')) for x in nodes];assert len(keys)==expected and len(set(keys))==expected
 summary=dict(name=name,expected=expected,tests=len(nodes),failures=sum(x.find('failure') is not None for x in nodes),errors=sum(x.find('error') is not None for x in nodes),skipped=sum(x.find('skipped') is not None for x in nodes),junit_suite_seconds=sum(float(x.get('time','0')) for x in xml.findall('testsuite')),junit_test_seconds=sum(float(x.get('time','0')) for x in nodes),terminal=terminal,input_count=len(source['inputs']),inputs_unchanged=True,nodes=keys)
 assert collected['count']==expected and terminal['returncode']==0 and summary['failures']==summary['errors']==summary['skipped']==0
 allnodes.extend(keys);batches.append(summary)
assert len(allnodes)==len(set(allnodes))==37
union=dict(count=37,overlap_count=0,nodes=sorted(allnodes),source_sha=sha,interpretation='Two original isolated pytest batches in parallel, 23 new API + (6 new UI +8 related) =37 unique selected nodes; independent repetition adds zero unique nodes to author selection')
write('union.json',union)
pages=[];databases=[];md=[];sqlproofs=[]
for batch in ['api','pages-related']:
 for current,dirs,files in os.walk(root/batch/'data',followlinks=False):
  dirs[:]=[d for d in dirs if not (Path(current)/d).is_symlink()]
  for name in files:
   p=Path(current)/name
   if p.is_symlink():continue
   rel=str(p.relative_to(root))
   if name=='result.json':
    value=json.loads(p.read_text());requests=value.get('requests',[])
    pages.append(dict(path=rel,case=value.get('case'),status=value.get('status'),checks=len(value.get('checks',[])),assets=len(value.get('assets',[])),recorded_api_attempts=len(requests),actual_api_replies=sum(isinstance(r.get('status'),int) for r in requests),actual_mutation_replies=sum(r.get('method') not in ('GET','HEAD') and isinstance(r.get('status'),int) for r in requests),synthetic_not_sent=sum(r.get('synthetic_phase')=='NOT_SENT' for r in requests),blobs=value.get('downloads',value.get('blobs',[]))))
   elif name.endswith('.md'):md.append(dict(path=rel,**digest(p)))
   elif name=='authority-before-body.json':sqlproofs.append(dict(path=rel,**digest(p),evidence=json.loads(p.read_text())))
   elif name.endswith('.db'):
    with sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True) as c:
     c.row_factory=sqlite3.Row
     tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
     counts={t:c.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
     runs=[dict(r) for r in c.execute('SELECT id,status,version,created_at,error FROM runs ORDER BY created_at,id')]
     attempts=[dict(r) for r in c.execute('SELECT status,count(*) n FROM attempts GROUP BY status')]
    databases.append(dict(path=rel,**digest(p),table_count=len(tables),table_rows=counts,runs=runs,attempt_ledger_states=attempts))
assert len(databases)==37 and len(sqlproofs)==2 and sum(len(x['evidence']['checked']) for x in sqlproofs)==6
starts=[datetime.datetime.fromisoformat(x['terminal']['started_at']) for x in batches];ends=[datetime.datetime.fromisoformat(x['terminal']['ended_at']) for x in batches]
proof=dict(source_sha=sha,batches=batches,union=union,parallel_wall_interval_seconds=(max(ends)-min(starts)).total_seconds(),junit_suite_seconds_sum=sum(x['junit_suite_seconds'] for x in batches),input_count=len(source['inputs']),whole_input_before_after_unchanged_per_batch=True,pages=pages,sqlite=databases,md_outputs=md,authority_before_body=sqlproofs,provenance=dict(page='Full served JavaScript/JSDOM and actual ASGI TestClient/SQLite; static asset response SHA checked by original pytest against snapshot input',requests='Page recorded API attempts; one controlled before-send synthetic failure has no server response. Fixture revoke command API replies are asserted, not separate browser fetch records',workers='Worker objects use same Store, not process restart; only synthetic Mock/Scripted model objects',sql='Original saved SQL trace text from each of three endpoint requests for each parent-output/child-output case after controlled stored receipt damage and Grant withdrawal',attempts='DB ledger state counts are not a separately instrumented total of provider calls',input_copies='Snapshot is reconstructible Git input, excluded from raw output manifest; exact Gitblob/SHA/size indices retained'))
write('proof.json',proof)
newpages=[p for p in pages if str(p['case']).startswith('correction-')]
newpage_summary=dict(cases=len(newpages),checks=sum(p['checks'] for p in newpages),recorded_api_attempts=sum(p['recorded_api_attempts'] for p in newpages),actual_api_replies=sum(p['actual_api_replies'] for p in newpages),assets=sum(p['assets'] for p in newpages),blobs=sum(len(p['blobs']) for p in newpages),actual_worker_objects='11 across six new pages (six parent objects plus five child objects); revoked case child remains QUEUED',child_synthetic_requests=14,parent_provider_total='Not separately instrumented in this independent wrapper; see original model-boundary files and DB attempt ledgers')
review=dict(verdict='FINITE_REVIEW_PASS',source_sha=sha,tests=dict(selected_unique=37,new_api=23,new_page=6,related=8,independent_repeat_additional_unique=0,failures=0,errors=0,skipped=0,batches=[{k:v for k,v in x.items() if k!='nodes'} for x in batches],parallel_wall_interval_seconds=proof['parallel_wall_interval_seconds'],junit_suite_seconds_sum=proof['junit_suite_seconds_sum']),inputs=dict(count=len(source['inputs']),per_batch_all_before_after_equal=True),static_review=json.loads((root/'static-review.json').read_text()),block_closure=dict(previous='7378 has 36PASS with static BLOCK, retained immutable in its original directory; never relabelled as this source',current='ID-only original-key lookup plus parent binding and parent/child independent metadata authority before full child Run/context; six actual403 endpoint paths and zero forbidden body SELECTs in saved original SQL traces'),new_page_summary=newpage_summary,side_effects='Each successful original artifact.save_text creates one Resource and two derived resource.read Grants; new controller adds no executor, role, or Grant type. Previous Goal/criteria/declaration/Run/artifacts remain unchanged.',boundaries=dict(real_model='NOT_RUN; only synthetic Mock/Scripted models',general_semantic_acceptance='NOT_RUN; ordinary automatic goal status stays NOT_RUN, technical result PARTIAL; human choices simulated separately',real_human_signoff='NOT_RUN',pg='NOT_RUN',native_browser='NOT_RUN; JSDOM',windows='NOT_RUN',separate_process_restart='NOT_RUN',ci='NOT_RUN',optional_independent_migration_probe='NOT_RUN; no extra probe added'),actions='Two isolated concurrent pytest batches once each, no retries or additional modules. Repository read-only; own new /tmp snapshot and evidence only.')
write('review.json',review)
manifest=[]
for current,dirs,files in os.walk(root,followlinks=False):
 dirs[:]=[d for d in dirs if d not in ('snapshot','pytest-cache','__pycache__') and not (Path(current)/d).is_symlink()]
 for name in files:
  p=Path(current)/name
  if p.is_symlink() or name in ('raw-manifest.json','raw-sha256sums.txt'):continue
  rel=str(p.relative_to(root));kind='derived-review' if name in ('review.json','proof.json','static-review.json','union.json') else 'reproduction-tool' if name in ('package.py','run-batch.py') else 'input-index' if name.startswith('source-') else 'derived-junit-index' if name=='collected.json' else 'raw-output'
  manifest.append(dict(path=rel,kind=kind,**digest(p)))
manifest.sort(key=lambda x:x['path'])
write('raw-manifest.json',dict(source_sha=sha,file_count=len(manifest),files=manifest,excluded=['snapshot/ reconstructible exact Git inputs; indices retained','pytest-cache/ disposable cache','symlink aliases and external installed node_modules link'],no_runtime_outputs_excluded=True))
(root/'raw-sha256sums.txt').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in manifest))
for item in manifest:assert digest(root/item['path'])=={k:item[k] for k in ('size','sha256')}
keys=['review.json','proof.json','raw-manifest.json','raw-sha256sums.txt','union.json','static-review.json','api/junit.xml','pages-related/junit.xml','api/source-after.json','pages-related/source-after.json','api/pytest.log','pages-related/pytest.log']
print(json.dumps(dict(source_sha=sha,verdict=review['verdict'],batches=[{k:v for k,v in x.items() if k!='nodes'} for x in batches],unique_nodes=37,overlap=0,parallel_wall_interval_seconds=proof['parallel_wall_interval_seconds'],new_page_summary=newpage_summary,sqlite=len(databases),sql_trace_files=len(sqlproofs),sql_endpoints=sum(len(x['evidence']['checked']) for x in sqlproofs),md_files=len(md),manifest_entries=len(manifest),key_hashes={k:digest(root/k) for k in keys}),ensure_ascii=False))
