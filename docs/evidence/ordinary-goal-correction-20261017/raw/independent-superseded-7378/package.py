import hashlib,json,os,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).parent
sha='7378b97ec0d85f821c9830290d5075e831270e33'
def write(name,value): (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def hashfile(p):
 d=p.read_bytes();return dict(size=len(d),sha256=hashlib.sha256(d).hexdigest())
terminal=json.loads((root/'terminal.json').read_text());before=json.loads((root/'source-before.json').read_text());after=json.loads((root/'source-after.json').read_text())
assert before['inputs']==after['inputs'] and after['identical_to_before']
suites=ET.parse(root/'junit.xml').getroot();nodes=list(suites.iter('testcase'))
junit=dict(tests=len(nodes),failures=sum(x.find('failure') is not None for x in nodes),errors=sum(x.find('error') is not None for x in nodes),skipped=sum(x.find('skipped') is not None for x in nodes),test_seconds=sum(float(x.get('time','0')) for x in nodes),suite_seconds=sum(float(x.get('time','0')) for x in suites.findall('testsuite')),nodes=[dict(classname=x.get('classname'),name=x.get('name'),seconds=x.get('time'),failure=x.find('failure') is not None,error=x.find('error') is not None,skipped=x.find('skipped') is not None) for x in nodes])
pages=[];md=[];dbs=[]
for current,dirs,files in os.walk(root/'data',followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(current)/d).is_symlink()]
 for name in files:
  p=Path(current)/name
  if p.is_symlink():continue
  rel=str(p.relative_to(root))
  if name=='result.json':
   value=json.loads(p.read_text()); reqs=value.get('requests',[])
   pages.append(dict(path=rel,case=value.get('case'),status=value.get('status'),checks=len(value.get('checks',[])),assets=len(value.get('assets',[])),recorded_api_attempts=len(reqs),actual_api_replies=sum(isinstance(r.get('status'),int) for r in reqs),actual_mutation_replies=sum(r.get('method') not in ('GET','HEAD') and isinstance(r.get('status'),int) for r in reqs),synthetic_before_send=sum(r.get('synthetic_phase')=='NOT_SENT' for r in reqs),blobs=value.get('downloads',value.get('blobs',[]))))
  elif name.endswith('.md'):md.append(dict(path=rel,**hashfile(p)))
  elif name.endswith('.db'):
   with sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True) as c:
    c.row_factory=sqlite3.Row
    tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts={t:c.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
    runrows=[dict(r) for r in c.execute('SELECT id,status,version,created_at,error FROM runs ORDER BY created_at,id')]
    states=[dict(r) for r in c.execute('SELECT status,count(*) n FROM attempts GROUP BY status')]
   dbs.append(dict(path=rel,**hashfile(p),table_count=len(tables),table_rows=counts,runs=runrows,attempt_ledger_states=states))
proof=dict(source_sha=sha,terminal=terminal,junit=junit,input_count=len(before['inputs']),inputs_unchanged=True,pages=pages,sqlite=dbs,md_outputs=md,all_data_preserved=True,source_and_test_copies='Reconstructible Git inputs excluded from raw manifest; exact Gitblob/SHA/size indices are preserved',provenance=dict(page='Full served JavaScript + JSDOM and actual ASGI TestClient/SQLite; clipboard/native browser not used',assets='Each served asset SHA checked against exact snapshot input by original pytest tests',attempts='Database ledger row counts, not independently instrumented provider total',revoke='New page revoke commands use original API version CAS; fixture command replies are asserted by driver, not separate browser-fetch raw requests',sql_trace='Original trace test asserts forbidden SELECT absent, but does not serialize its trace list; raw DB/source/JUnit retained'))
write('proof.json',proof)
review=dict(verdict='BLOCK',source_sha=sha,dynamic_result=junit,static_findings=[json.loads((root/'static-block.json').read_text())],previous_findings=dict(identifier_authority='CLOSED in this source for direct child GET: independent parent material/effect metadata authorization precedes feedback body',revocation_redaction='CLOSED: source section removed; redacted workspace caches and recovery403 clear protected result',detached_controls='CLOSED: section.isConnected fences same-Run redraw and navigation; pending same-key metadata controls rebuilt'),contract_review=dict(preview='No TTL; project-lock admission recomputes full rejection CAS twice before commit',source='Same prospective Goal/criteria/material snapshot; one correction edge and at most one child; no old Goal/ledger/Run/output rewrite',post_admission='Only grant_version removed from stable signed evidence comparison; current required source/output authority and exact latest rejection repeated',execution='Original Worker/registered tools; frozen mock policy + worker live gate; own Run created_at/limits, max_repairs0',declaration='Child starts separate PENDING and remains PARTIAL/NOT_RUN; simulated explicit declaration does not prove semantics'),scope=dict(new_api=22,new_page=6,related=8,unique_nodes=len(nodes),independent_repeats_of_author_selection=True,additional_unique_nodes=0,selector_correction='Actual owner UI [revocation], requested [revoked] did not exist; parent notified before execution'),boundaries=dict(real_model='NOT_RUN, only synthetic Mock/Scripted objects',general_semantics='NOT_RUN',real_human_acceptance='NOT_RUN; scripted choices/reasons only',process_restart='NOT_RUN; Worker objects use same Store',pg='NOT_RUN',native_browser='NOT_RUN; JSDOM',windows='NOT_RUN',ci='NOT_RUN',new_roles_or_grant_types=False,artifact_effect='Successful original save_text creates one Resource + two derived read Grants; no claim of zero Grant rows'),actions='One frozen batch only; no retry, no extra test module, no repository writes. Green tests cannot clear the static authorization-order BLOCK.')
write('review.json',review)
manifest=[]
for current,dirs,files in os.walk(root,followlinks=False):
 dirs[:]=[d for d in dirs if d not in ('snapshot','pytest-cache','__pycache__') and not (Path(current)/d).is_symlink()]
 for name in files:
  p=Path(current)/name
  if p.is_symlink() or name in ('raw-manifest.json','raw-sha256sums.txt'):continue
  rel=str(p.relative_to(root));kind='derived-review' if name in ('proof.json','review.json','static-block.json') else 'reproduction-tool' if name in ('run.py','package.py') else 'input-index' if name.startswith('source-') else 'raw-output'
  manifest.append(dict(path=rel,kind=kind,**hashfile(p)))
manifest.sort(key=lambda x:x['path'])
write('raw-manifest.json',dict(source_sha=sha,files=manifest,file_count=len(manifest),excluded=['snapshot/ reconstructible Git inputs; hashes preserved','pytest-cache/ disposable pytest cache','symlink aliases and external node_modules dependency link'],no_runtime_outputs_excluded=True))
(root/'raw-sha256sums.txt').write_text(''.join(f"{i['sha256']}  {i['path']}\n" for i in manifest))
for item in manifest:assert hashfile(root/item['path'])=={k:item[k] for k in ('size','sha256')}
print(json.dumps(dict(source_sha=sha,terminal=terminal,junit={k:v for k,v in junit.items() if k!='nodes'},sqlite_files=len(dbs),pages=pages,md_outputs=md,manifest_entries=len(manifest),key_hashes={n:hashfile(root/n) for n in ['review.json','proof.json','raw-manifest.json','raw-sha256sums.txt','source-after.json','junit.xml','pytest.log','static-block.json']}),ensure_ascii=False))
