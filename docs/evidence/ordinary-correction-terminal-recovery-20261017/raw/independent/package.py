import hashlib,json,os,sqlite3,xml.etree.ElementTree as E
from pathlib import Path
root=Path(__file__).parent;sha='9f7d881789ce07e2b5868919e5a3f9a794c6ff3b'
def digest(p):
 b=p.read_bytes();return dict(size=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(name,value):(root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
before=json.loads((root/'source-before.json').read_text());after=json.loads((root/'source-after.json').read_text());assert before['inputs']==after['inputs'] and after['identical_to_before']
terminal=json.loads((root/'terminal.json').read_text());xml=E.parse(root/'junit.xml').getroot();nodes=list(xml.iter('testcase'));junit=dict(tests=len(nodes),failures=sum(x.find('failure') is not None for x in nodes),errors=sum(x.find('error') is not None for x in nodes),skipped=sum(x.find('skipped') is not None for x in nodes),suite_seconds=sum(float(x.get('time','0')) for x in xml.findall('testsuite')),nodes=[dict(classname=x.get('classname'),name=x.get('name'),seconds=x.get('time')) for x in nodes]);assert terminal['returncode']==0 and junit['tests']==3 and junit['failures']==junit['errors']==junit['skipped']==0
files=[];dbs=[]
for current,dirs,names in os.walk(root/'data',followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(current)/d).is_symlink()]
 for name in names:
  p=Path(current)/name
  if p.is_symlink():continue
  files.append(p)
  if name.endswith('.db'):
   with sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True) as c:
    c.row_factory=sqlite3.Row
    tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts={t:c.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
    rows=[dict(r) for r in c.execute('SELECT id,status,fence,version,lease_until,error FROM runs ORDER BY created_at,id')]
   dbs.append(dict(path=str(p.relative_to(root)),**digest(p),table_count=len(tables),table_rows=counts,runs=rows))
def original(name):
 found=[p for p in files if p.name==name];assert len(found)==1;return found[0],json.loads(found[0].read_text())
rp,r=original('lease-recovery.json');hp,http=original('terminal-http.json');sp,stability=original('terminal-stability.json');ip,initial=original('known-save-rejected-final.json')
assert r['initial']['status']=='RUNNING' and r['initial']['error'] is None and r['initial']['result'] is None
assert r['terminal']['status']=='FAILED' and r['terminal']['error']['code']=='VERSION_CONFLICT' and r['terminal']['result'] is None and r['terminal']['lease_until']==0
assert r['terminal']['fence']==r['initial']['fence']+2 and r['preserved_before']==r['preserved_after'] and r['recovery_mock_requests']==0
assert [e['kind'] for e in r['recovery_events']]==['WORKER_LOST','RECONCILED','CLAIMED','CONTRACT_REJECTED']
assert http['history']['status']==200 and http['detail']['status']==409 and http['artifact']['status']==200
artifact=http['artifact']['body'];artifact_hash=hashlib.sha256(artifact['content'].encode()).hexdigest();assert artifact_hash==artifact['hash'];assert stability['no_later_work'] and stability['stale_finalizer']['code']=='VERSION_CONFLICT'
proof=dict(source_sha=sha,input_count=len(before['inputs']),all_input_bytes_unchanged=True,src_schemas_identical_to=before['production_src_schemas_identical_to'],terminal=terminal,junit=junit,sqlite=dbs,recovery=dict(initial_status=r['initial']['status'],initial_error=r['initial']['error'],terminal_status=r['terminal']['status'],error=r['terminal']['error'],fence_before=r['initial']['fence'],fence_after=r['terminal']['fence'],lease_after=r['terminal']['lease_until'],recovery_events=r['recovery_events'],preserved_tables=list(r['preserved_before']['tables']),all_preserved_tables_and_parent_equal=True,initial_child_mock_requests=r['original_mock_requests'],recovery_mock_requests=r['recovery_mock_requests'],real_model_requests=0,clock_scope=r['clock_scope'],stale_finalizer=stability['stale_finalizer'],later_once_no_work=stability['no_later_work']),http=dict(history_status=http['history']['status'],full_detail_status=http['detail']['status'],artifact_status=http['artifact']['status'],artifact_bytes=len(artifact['content'].encode()),artifact_sha256=artifact_hash),original_paths={p.name:str(p.relative_to(root)) for p in [rp,hp,sp,ip]},scope='One strengthened preexisting terminal case plus unchanged successful MD and read-only correction cases, three selected nodes; not an additional 37-node run')
write('proof.json',proof)
review=dict(verdict='FINITE_REVIEW_PASS_NO_PRODUCTION_FIX_REQUIRED',source_sha=sha,test_scope=junit,inputs=dict(count=len(before['inputs']),before_after_equal=True,production_src_schema_no_diff_from='d4c02072a40ac98075cfebaf22d23cb8cd24cbc4'),findings=dict(old_gap='Previous test asserted merely non-PARTIAL, so RUNNING/null result/error was a captured intermediate state, not terminal proof or a manufactured production red',existing_recovery='Actual Store.claim expiry reconciliation and Worker.process initial frozen-contract rejection flow reaches FAILED via Worker.once outer fenced handler',clock='Only module-bound db/worker time proxies after original HB joined; before and after actual lease time; no Run/lease rewrite or wall sleep',effects='Exact all-row equality of 12 evidence tables plus parent and child context, recovered model0 and preserved verified save prove no new durable save/model/reservation effects',dispatch_wording='No extra dispatch spy was run. Zero tool dispatch is a source control-flow inference: failure at worker.py442 before loop. Dynamic claim is no repeated save effect/record.',access='Metadata history exposes FAILED while full invalid contract remains409; existing authorized artifact GET200 exact original bytes',stale='Original stale finalizer raisesVERSION_CONFLICT; later Worker.once has no work and terminal/evidence stay unchanged'),boundaries=dict(real_model='NOT_RUN',real_human_semantics='NOT_RUN; simulated rejection/withdrawal',pg='NOT_RUN',native_browser='NOT_RUN',windows='NOT_RUN',process_restart='NOT_RUN; Worker objects share Store',ci='NOT_RUN',p_b='NOT_IMPLEMENTED/NOT_TESTED in this task',previous_37='Previously executed d731 batch remains separate; not rerun or relabelled'),actions='One independent three-node batch once, no retries, no source/test edits. Only own new /tmp snapshot and evidence writes.')
write('review.json',review)
manifest=[]
for current,dirs,names in os.walk(root,followlinks=False):
 dirs[:]=[d for d in dirs if d not in ('snapshot','pytest-cache','__pycache__') and not (Path(current)/d).is_symlink()]
 for name in names:
  p=Path(current)/name
  if p.is_symlink() or name in ('raw-manifest.json','raw-sha256sums.txt'):continue
  kind='derived-review' if name in ('review.json','proof.json') else 'reproduction-tool' if name in ('run.py','package.py') else 'input-index' if name.startswith('source-') else 'derived-junit-index' if name=='collected.json' else 'raw-output'
  manifest.append(dict(path=str(p.relative_to(root)),kind=kind,**digest(p)))
manifest.sort(key=lambda x:x['path']);write('raw-manifest.json',dict(source_sha=sha,file_count=len(manifest),files=manifest,excluded=['snapshot/ reconstructible Git inputs, exact Gitblob/SHA/size indices retained','pytest-cache disposable files','symlink aliases'],no_runtime_outputs_excluded=True));(root/'raw-sha256sums.txt').write_text(''.join(f"{i['sha256']}  {i['path']}\n" for i in manifest))
for i in manifest:assert digest(root/i['path'])=={k:i[k] for k in ('size','sha256')}
keys=['review.json','proof.json','raw-manifest.json','raw-sha256sums.txt','source-after.json','junit.xml','pytest.log','commands.json','terminal.json']
print(json.dumps(dict(source_sha=sha,junit=junit,terminal=terminal,input_count=len(before['inputs']),sqlite_files=len(dbs),artifact_bytes=proof['http']['artifact_bytes'],artifact_sha256=artifact_hash,preserved_tables=len(r['preserved_before']['tables']),manifest_entries=len(manifest),key_hashes={k:digest(root/k) for k in keys}),ensure_ascii=False))
