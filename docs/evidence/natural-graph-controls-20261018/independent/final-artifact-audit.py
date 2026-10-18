"""Pure-file/local-Git audit of closed graph-controls evidence. No DB/product import."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,subprocess,xml.etree.ElementTree as ET
R=Path('/workspace/natural-graph-controls-20261018');C=R/'actual-tmp/test_fresh_natural_app_derives0'
O=Path('/workspace/next-product-value-triage-20261018');REPO=Path('/workspace/Sim2Act')
F='d9e19b2829221909b49fd075b721d4e831d711a4';B='4a5fa568d2aefcbe59ef2f14c5a58414073bbe0b'
def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def fp(x):return sha(canonical(x).encode())
def git(*a):return subprocess.check_output(['git','-c','core.fsmonitor=false',*a],cwd=REPO)
def one(rows,label):
 assert len(rows)==1,(label,len(rows))
 return rows[0]
exe=load(R/'execution.json');assert exe['head']==F and exe['exit_code']==0 and exe['input_drift'] is False
assert '480s' in exe['command']
tests=ET.parse(R/'junit.xml').getroot().findall('.//testcase');assert len(tests)==1 and not tests[0].findall('failure') and not tests[0].findall('error') and not tests[0].findall('skipped')
assert tests[0].get('name')=='test_fresh_natural_app_derives_and_controls_edit_locks_from_page'
before=load(R/'inputs-before.json');after=load(R/'inputs-after.json');assert before['head']==after['head']==F and before['inputs']==after['inputs'] and len(before['inputs'])==693
for p,v in before['inputs'].items():
 b=(REPO/p).read_bytes();assert {'bytes':len(b),'sha256':sha(b)}==v,p
prod={p:v for p,v in before['inputs'].items() if p.startswith('src/')};assert len(prod)==133
assert git('rev-parse','HEAD').decode().strip()==F
assert git('diff','--name-only',B,F,'--','src').decode().splitlines()==['src/sim2act/web/app.js','src/sim2act/web/manual-locks.js']
for p,v in prod.items():
 b=git('show',F+':'+p);assert {'bytes':len(b),'sha256':sha(b)}==v
proof=load(C/'proof.json');page=load(C/'results.json');assert proof['status']==page['status']=='PASS' and page['error'] is None and not page['page_errors']
direct=proof['production_sha256'];assert len(direct)==131 and all(prod[p]['sha256']==s for p,s in direct.items())
extra=sorted(set(prod)-set(direct));assert len(extra)==2
assert len(page['checks'])==44 and len(page['actions'])==26 and len(page['requests'])==54 and len(page['static_resource_loads'])==27 and page['boots']==1
assert page['lifecycle']==[{'owned_http':0,'owned_actions':0}]
rows=[json.loads(x) for x in (C/'http-responses.jsonl').read_text().splitlines()];assert len(rows)==54
assert Counter(canonical(x) for x in rows)==Counter(canonical(x) for x in page['requests'])
for row in rows:
 assert sha(row['response_text'].encode())==row['response_utf8_sha256']
 assert row['response']==json.loads(row['response_text'])
 if row['body_text'] is None:assert row['body'] is None and row['body_sha256'] is None
 else:assert sha(row['body_text'].encode())==row['body_sha256'] and json.loads(row['body_text'])==row['body']
assets=page['static_resource_loads'];assert len({x['path'] for x in assets})==27
for asset in assets:
 b=(REPO/'src/sim2act/web'/(asset['path'].lstrip('/') or 'index.html')).read_bytes()
 assert asset['status']==200 and len(b)==asset['bytes'] and sha(b)==asset['sha256']
posts=[x for x in page['requests'] if x['method']=='POST'];assert len(posts)==7 and [x['status'] for x in posts]==[201,201,201,400,201,201,201]
assert [x['path'].rsplit('/',1)[-1] for x in posts]==['derive','manual-locks','derive','previews','manual-locks','derive','previews']
assert proof['posts']==[{'path':x['path'],'status':x['status']} for x in posts]
info=load(C/'info.json');aid=info['app'];iid=info['instance'];pid=info['project']
assert page['original_draft']['id']==aid and page['original_draft']['candidate']['namespace']=='pa-natural-spec-app.v1'
original=page['original_instance'];assert original['id']==iid and original['data_version']==0 and original['data']==[] and original['runs']==[]
assert len(page['original_releases'])==1
assert any(x['method']=='GET' and x['path']==f'/api/projects/{pid}/apps/{aid}/delivery-graph' and x['status']==409 for x in rows)
graphs=[page[k] for k in ('first_graph','locked_graph','unlocked_graph')]
for index,graph in enumerate(graphs):
 body={k:v for k,v in graph['graph'].items() if k!='graph_fingerprint'}
 assert fp(body)==graph['graph_fingerprint']==graph['graph']['graph_fingerprint']
 assert graph['app_id']==aid and graph['project_id']==pid and graph['candidate_fingerprint']==page['original_draft']['fingerprint']
 node=one([x for x in graph['graph']['nodes'] if x['key']==info['changed_node_key']],'node')
 assert node['locked'] is (index==1)
 assert graph['owner_acceptance']=='PENDING' and graph['semantic_status']=='UNKNOWN' and graph['publishable'] is False
 assert [(x['key'],x['id']) for x in graph['graph']['nodes']]==[(x['key'],x['id']) for x in graphs[0]['graph']['nodes']]
 made={k:v for k,v in posts[[0,2,5][index]]['response'].items() if k!='cached'}
 assert made==graph
for index,locked in ((1,True),(4,False)):
 post=posts[index];receipt=page['lock_receipt' if locked else 'unlock_receipt']
 assert receipt['lock']['locked'] is locked and receipt['lock']['revision']==(1 if locked else 2)
 assert post['body']['locked'] is locked and post['body']['expected_lock_revision']==(0 if locked else 1)
 assert receipt['lock']['node_id']==post['body']['change']['node_id']
 assert receipt['request_key']==post['body']['request_key'] and receipt['is_current'] is True
 assert receipt['receipt_status']=='CURRENT' and receipt['business_write_performed'] is False
 normalize=lambda v:{k:x for k,x in v.items() if k!='cached'}
 assert normalize(receipt)==normalize(post['response'])
 get=one([x for x in rows if x['method']=='GET' and x['path'].endswith('/manual-locks/receipt?request_key='+post['body']['request_key'])],'lock GET')
 assert normalize(get['response'])==normalize(receipt)
blocked=posts[3];error=blocked['response']['error'];reject=error['submission_rejection']
assert blocked['status']==400 and error['code']=='LOCK_CONFLICT' and reject['request_key']==blocked['body']['request_key'] and reject['request_fingerprint']==fp(blocked['body'])
assert reject['acceptance']=='NOT_ACCEPTED' and reject['previous_request']=='ABSENT' and reject['phase']=='TX_ROLLED_BACK'
preview=page['accepted_preview'];assert posts[6]['response']==preview and fp({k:v for k,v in preview.items() if k!='preview_fingerprint'})==preview['preview_fingerprint']
assert preview['context']['instance_id']==iid and preview['context']['graph_fingerprint']==graphs[-1]['graph_fingerprint']
assert preview['owner_acceptance']=='PENDING' and preview['semantic_status']=='UNKNOWN' and preview['effective_candidate']['actions'][2]['revision']==2
assert blocked['body']['request_key']!=posts[6]['body']['request_key']
# Reconstruct exactly eleven EXPECTED journal headers from actual wires. Stored rows are not retained here.
expected=set()
for row in posts:
 key=row['body']['request_key']
 if row['status']==400:continue
 if row['path'].endswith('/derive'):expected.add((aid,'derive',key))
 elif row['path'].endswith('/manual-locks'):
  expected|={(aid,k,key) for k in ('lock','manual_edit_lock','manual_edit_lock_seal')}
 else:expected|={(iid,k,key) for k in ('natural-local-logic.v1.preview','natural-local-logic.v1.preview_seal')}
assert len(expected)==11 and all(x[2]!=blocked['body']['request_key'] for x in expected)
assert len(proof['protected_tables_unchanged'])==50 and len(proof['changed_tables'])==5 and not set(proof['protected_tables_unchanged'])&set(proof['changed_tables'])
assert len(load(C/'generation-wire.json'))==proof['generation_mock_requests']==3
assert proof['page_model_requests']==proof['page_worker_calls']==proof['real_model_requests']==proof['business_data_writes']==0
assert page['business_worker']==page['check_worker']==page['real_model']=='NOT_RUN'
# Validate the exact strict helper/call in the frozen executed test source without importing it.
source=git('show',F+':tests/test_natural_graph_controls_ui.py');tree=ast.parse(source)
helper=one([x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='exact_graph_metadata'],'strict helper')
assert any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='exact_graph_metadata' for x in ast.walk(tree))
assert b'assert len(expected) == len(journal) == 11' in source and b'assert before[table] == after[table], table' in source
assert b'row["snapshot"] == dict(request=request, response=response)' in source
qualification=load(R/'qualification.json')
result={'status':'PASS_LIMITED_NONAUTHOR_SOURCE_AND_FILE_AUDIT','source':F,'baseline':B,'reviewer_product_or_pytest_run':False,'database_file_open_or_sql':False,'network_http_model_by_reviewer':False,
 'source_changed_production':['src/sim2act/web/app.js','src/sim2act/web/manual-locks.js'],'execution_inputs':693,'tracked_production':133,'direct_production':131,'tracked_production_not_in_direct_filter':extra,'drift':[],
 'current_junit':{'pass':1,'seconds':float(tests[0].get('time')),'node':tests[0].get('name')},'outer_seconds':exe['elapsed_seconds'],
 'counts':{'checks':44,'actions':26,'api':54,'assets':27,'total_page_http':81,'boots':1,'posts':7,'generation_mock':3,'page_model':0,'business_worker':0,'real_model':0},
 'post_statuses':[x['status'] for x in posts],'raw_api_text_and_sha_independently_verified':54,'asset_sha_independently_verified':27,'actual_graphs_independently_hashed':3,
 'expected_journal_headers_reconstructed_from_wires':[list(x) for x in sorted(expected)],
 'table_evidence_limit':'All55-table comparisons and exact11 actual stored journals/3anchors/state/sourceVersions/lock were executed by the successful frozen pytest. Only fingerprints,50protected/5changed lists and HTTP values are retained; reviewer inspected strict oracle and PASS but did not independently recalculate stored table rows or journal fingerprints, and did not open fixture.db.',
 'prior_attempt':'First failure remains FAIL exit1,23 completed checks; server400 LOCK_CONFLICT and NOT_ACCEPTED proof retained. UI literal mismatch cause is code inference because actual first UI status was NOT_RETAINED. Exact corrected predicate and14 retained file hashes were independently reviewed earlier in this directory.',
 'attempts':{'unique_node':1,'executions':2,'pass':1,'failure':1,'saved_mock_total':6},
 'limits':['PA actual only; shared natural namespace supports PB by source review, no new PB actual run','JSDOM actual loopback HTTP, not native browser/Windows','No business/CHECK Worker, CHECK/version/commit/new-input long chain rerun','No real model or human semantic acceptance, PG, CI, deployment, cancelled window or new recovery matrix']}
(O/'final-artifact-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
