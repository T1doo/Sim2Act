"""Closed-artifact/local-Git audit only; no product import, database, HTTP or model."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,subprocess,xml.etree.ElementTree as ET
A=Path('/workspace/project-run-results-20261018');R=A/'attempt-2';C=R/'actual-tmp/test_project_history_opens_ori0';O=Path('/workspace/product-results-gap-triage-20261018');REPO=Path('/workspace/Sim2Act')
OLD='49e0e7b026126ba031141944b15f20e28b4358a7';F='c3aa1e4fa569e6ea08174e30811f216392b7ccd2';B='2c21d278dbe0d46e05c4ba4cccd473a8edfa4716'
def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def fp(v):return sha(canonical(v).encode())
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=REPO)
def one(rows,label):
 assert len(rows)==1,(label,len(rows))
 return rows[0]
# First failed observer attempt: never touch its database; verify all other manifest bytes.
fm=load(A/'first-failure-manifest.json');assert len(fm['files'])==9
first_verified=[];first_db=[]
for path,meta in fm['files'].items():
 if path.endswith('.db'):
  assert (A/path).stat().st_size==meta['bytes'];first_db.append({'path':path,**meta,'reviewer_status':'Provided SHA recorded and stat bytes matched; DB contents not read.'});continue
 b=(A/path).read_bytes();assert len(b)==meta['bytes'] and sha(b)==meta['sha256'];first_verified.append(path)
assert len(first_verified)==8 and len(first_db)==1
first_input=load(A/'inputs-before.json');assert first_input['inputs']==load(A/'inputs-after.json')['inputs'] and len(first_input['inputs'])==695
firstcase=A/'actual-tmp/test_project_history_opens_ori0';assert load(firstcase/'mock-wire.json')==[]
fh=load(firstcase/'fixture-http.json');assert len(fh)==11
for row in fh:assert sha(row['response_text'].encode())==row['sha256']
last=json.loads(fh[-1]['response_text']);assert fh[-1]['status']==200 and last['namespace']=='INTERNAL_APPRUN' and last['status']=='SUCCEEDED' and last['result_version']==1
firstxml=ET.parse(A/'junit.xml').getroot().findall('.//testcase');assert len(firstxml)==1 and firstxml[0].find('failure') is not None
failure=firstxml[0].find('failure').text or '';assert 'assert (3 == 3 and 1 == 1 and 0 == 4)' in failure
assert load(A/'execution.json')['exit_code']==1
assert not (firstcase/'results.json').exists() and not (firstcase/'proof.json').exists()
assert git('diff','--name-only',OLD,F).decode().splitlines()==['tests/test_project_run_result_ui.py']
assert git('diff',OLD,F,'--','src')==b''
assert git('show',OLD+':tests/project_run_result_ui.cjs')==git('show',F+':tests/project_run_result_ui.cjs')
oldtree=ast.parse(git('show',OLD+':tests/test_project_run_result_ui.py'));newtree=ast.parse(git('show',F+':tests/test_project_run_result_ui.py'))
asserts=lambda t:[ast.dump(x,include_attributes=False) for x in ast.walk(t) if isinstance(x,ast.Assert)]
assert asserts(oldtree)==asserts(newtree)
instrument={'result':'NO_QUALITY_REGRESSION_IN_TEST_RECORDER_CORRECTION','old_source':OLD,'new_source':F,'changed_path':'tests/test_project_run_result_ui.py',
 'source_reason':'Installed httpx MockTransport.handle_async_request invokes handler directly and never handle_request; correction awaits the original async method, records response, returns it unchanged, and retains the transport class. Sync original wrapper retained; no Worker isinstance/auth/budget changes.',
 'unchanged_assert_ast_count':len(asserts(oldtree)),'production_and_cjs_equal':True,
 'first_attempt':{'exit':1,'outer_seconds':load(A/'execution.json')['elapsed_seconds'],'junit_seconds':float(firstxml[0].get('time')),'failure':'(3 == 3 and 1 == 1 and 0 == 4)','fixture_http_count':11,'last_run_status':'SUCCEEDED','last_result_version':1,'page_started':False,'mock_wire_saved':0,'models_count_evidence':'Generation3 and business1 counts in original failed assertion and fixture terminal; no complete raw model capture.','inputs':695,'drift':[]},
 'first_manifest':{'entries':9,'non_database_files_full_bytes_verified':first_verified,'database_not_read':first_db},'second_attempt':'Audited separately below, not inferred from recorder fix.'}
(O/'instrumentation-review.json').write_text(json.dumps(instrument,ensure_ascii=False,indent=2)+'\n')
# Qualified current attempt.
exe=load(R/'execution.json');assert exe['head']==F and exe['exit_code']==0 and exe['input_drift'] is False
cases=ET.parse(R/'junit.xml').getroot().findall('.//testcase');assert len(cases)==1 and not cases[0].findall('failure') and not cases[0].findall('error') and not cases[0].findall('skipped')
before=load(R/'inputs-before.json');after=load(R/'inputs-after.json');assert before['head']==after['head']==F and before['inputs']==after['inputs'] and len(before['inputs'])==695
prod={p:v for p,v in before['inputs'].items() if p.startswith('src/')};assert len(prod)==133
for p,meta in before['inputs'].items():
 b=(REPO/p).read_bytes();assert {'bytes':len(b),'sha256':sha(b)}==meta,p
for p,meta in prod.items():
 b=git('show',F+':'+p);assert {'bytes':len(b),'sha256':sha(b)}==meta and b==git('show',OLD+':'+p)
assert git('diff','--name-only',B,F,'--','src').decode().splitlines()==['src/sim2act/web/app.js']
proof=load(C/'proof.json');page=load(C/'results.json');info=load(C/'info.json');assert proof['status']==page['status']=='PASS' and page['error'] is None and not page['page_errors']
assert len(page['checks'])==29 and len(page['actions'])==9 and len(page['requests'])==33 and len(page['static_resource_loads'])==27
assert page['downloads']==[] and page['lifecycle']==[{'owned_http':0,'owned_actions':0}]
assert len(proof['production_sha256'])==133 and all(prod[p]['sha256']==v for p,v in proof['production_sha256'].items())
rows=[json.loads(x) for x in (C/'http-responses.jsonl').read_text().splitlines()];assert len(rows)==33
# The one held row receives delivery_released=true after its original incremental log write.
normalize=lambda row:{k:v for k,v in row.items() if k!='delivery_released'}
assert Counter(canonical(x) for x in rows)==Counter(canonical(normalize(x)) for x in page['requests'])
for row in page['requests']:
 assert row['method']=='GET' and row['body'] is None and row['body_text'] is None and row['body_sha256'] is None
 assert sha(row['response_text'].encode())==row['response_utf8_sha256'] and json.loads(row['response_text'])==row['response']
for asset in page['static_resource_loads']:
 b=(REPO/'src/sim2act/web'/(asset['path'].lstrip('/') or 'index.html')).read_bytes()
 assert asset['status']==200 and asset['bytes']==len(b) and asset['sha256']==sha(b)
assert len({x['path'] for x in page['static_resource_loads']})==27
selected=page['selected_run'];assert selected['namespace']=='INTERNAL_APPRUN' and selected['id']==info['run'] and selected['instance_id']==info['instance'] and selected['release_id']==info['release'] and selected['app_run_id']==info['app_run'] and selected['status']=='SUCCEEDED'
opened=page['opened_scope'];assert opened['workspace']=='apps' and opened['project']==info['project'] and opened['active_app']==info['app'] and opened['active_run']==info['run']
assert opened['engineering']=={'app':info['app'],'instance':info['instance'],'run':info['run'],'app_run':info['app_run']}
assert opened['owner']=={'instance':info['instance'],'run':info['run']} and opened['owner_sequence']==0 and opened['owner_acceptance']=='PENDING' and opened['result_version']==1
assert 'undefined' not in opened['result_text'] and '0 模型请求' not in opened['result_text']
ownerrows=[x for x in page['requests'] if x['path'].endswith('/spec-owner-review')];assert ownerrows
for row in ownerrows:
 v=row['response'];contract=v['current'];assert v['owner_acceptance']=='PENDING' and v['sequence']==0 and not v['history']
 assert (contract['run_id'],contract['app_run_id'],contract['instance_id'],contract['release_id'],contract['result_version'])==(info['run'],info['app_run'],info['instance'],info['release'],1)
 assert contract['output']==selected['result'] and contract['output_fingerprint']==fp(contract['output'])
artifact=page['artifact_proof'];row=page['requests'][artifact['request_index']];saved=row['response'];output=selected['result']
assert row['status']==200 and row['path']==artifact['path']=='/api/internal/app-run-jobs/'+info['run']+'/spec-artifact'
assert row['response_utf8_sha256']==artifact['response_utf8_sha256']
for k,v in [('project_id',info['project']),('app_id',info['app']),('instance_id',info['instance']),('run_id',info['run']),('app_run_id',info['app_run']),('release_id',info['release']),('result_version',1)]:assert saved[k]==v
assert saved['output_fingerprint']==artifact['output_fingerprint']==fp(output)
assert saved['resource']['resource_id']==output['resource_id']==artifact['resource_id']
assert saved['resource']['content']==canonical(output['checklist']) and saved['resource']['hash']==output['hash']==sha(saved['resource']['content'].encode())==artifact['content_utf8_sha256']
assert saved['owner_acceptance']=='PENDING' and saved['semantic_status']=='UNKNOWN' and saved['new_model_requests']==saved['project_writes']==0 and saved['formal_publication_enabled'] is False
held=page['delayed_actual_instance_response'];heldrow=page['requests'][held['request_index']]
assert held['server_received'] and held['response_complete_before_hold'] and held['released'] and heldrow['delivery_released'] is True
assert heldrow['status']==held['status']==200 and heldrow['response_utf8_sha256']==held['response_utf8_sha256'] and heldrow['path']==held['path']=='/api/internal/instances/'+info['instance']
expected={'project':info['other_project'],'workspace':'projects','active_app':None,'active_run':None,'engineering':None,'owner':None,'internal_visible':False,'internal_data_text':'','result_text':''}
assert held['scope_before_release']==held['scope_after_release']==page['other_project_scope']==expected
# No follow-up request after the explicit held-response release event.
events=[json.loads(x) for x in (C/'page-progress.jsonl').read_text().splitlines()];releaseindex=next(i for i,e in enumerate(events) if e['event']=='release_actual_instance_response')
assert not any(e['event']=='http_start' for e in events[releaseindex+1:])
syn=page['synthetic_renderer_compatibility'];assert syn['classification']=='CONTROLLED_ISOLATED_RENDERER_NOT_ACTUAL_BACKEND' and syn['input']['sum']=='9007199254740993.01' and syn['http_requests']==0 and syn['navigation_button_present'] is False
assert '金额 合计 9007199254740993.01，共 2 条记录。' in syn['rendered_text']
assert proof['before_fingerprint']==proof['after_fingerprint'] and proof['changed_tables']==[] and len(proof['protected_tables_unchanged'])==len(proof['table_fingerprints'])==55
assert set(proof['protected_tables_unchanged'])==set(proof['table_fingerprints'])
for table,v in proof['table_fingerprints'].items():assert isinstance(v['rows'],int) and len(v['sha256'])==64
mocks=load(C/'mock-wire.json');assert len(mocks)==4
for m in mocks:assert m['status']==200 and sha(m['response_text'].encode())==m['sha256'] and isinstance(json.loads(m['request_text']),dict)
assert proof['generation_mock_requests']==3 and proof['fixture_business_mock_requests']==proof['fixture_business_worker_calls']==1 and proof['mock_requests']==4
assert proof['page_worker_calls']==proof['real_model_requests']==proof['page_post_requests']==0
result={'status':'PASS_LIMITED_NONAUTHOR_FILE_AND_SOURCE_AUDIT','source':F,'production_equals_49e0':True,'production_changed_from_2c21':['src/sim2act/web/app.js'],'inputs':695,'production':133,'drift':[],
 'current_junit':{'pass':1,'seconds':float(cases[0].get('time')),'name':cases[0].get('name')},'outer_seconds':exe['elapsed_seconds'],
 'counts':{'unique_pytest_node':1,'attempts':2,'pass':1,'observer_failure_before_page':1,'checks':29,'actions':9,'api_get':33,'assets':27,'page_http_total':60,'post':0,'download':0,'page_worker':0,'final_mock_raw':4,'final_generation_mock':3,'final_fixture_business_mock':1,'total_observed_mock_calls_both_attempts':8,'complete_model_raw_attempts':1,'real_model':0},
 'artifact':artifact,'held_scope':expected,'csv_renderer':'Explicit synthetic only; exact string preserved; no CSV backend regression execution.',
 'table_limit':'Frozen successful pytest executed before==after over all55 tables; proof retains equal globalFP and55 table rowcounts/FP, not full rows. Reviewer checked strict oracle/PASS/FP metadata and did not independently recompute raw table equality or query DB.',
 'method':'Pure closed files/local Git/AST only. No product/pytest/HTTP/model/network/DB/SQL by reviewer.',
 'scope_limits':['Actual PA normal navigation, double-click and one complete-HTTP200 delayed delivery across project switch only.','Other account/reconnect/app/workspace/same-view instance/Run supersession and background-refresh behavior source-reviewed, not all actual negative cases.','PB dynamic/native/Windows/PG/real model/semantic/human/CI/deploy not executed.','First observer FAIL retained; first4 model calls have counter/fixture evidence, mock-wire empty. Only qualified second4 have complete raw model request/response capture.']}
(O/'final-artifact-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
