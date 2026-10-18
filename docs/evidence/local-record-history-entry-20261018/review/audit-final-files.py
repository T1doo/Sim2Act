"""Closed file/source review only; no application, SQL, subprocess or network."""
import hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

root=Path('/workspace/local-record-history-entry-20261018')
out=Path('/workspace/local-record-history-entry-review-20261018')
repo=Path('/workspace/Sim2Act')
def read(path): return json.loads(path.read_text())
def sha(raw): return hashlib.sha256(raw).hexdigest()
manifest=(root/'sealed-manifest.json').read_bytes()
assert sha(manifest)=='b8952e83b82d62326934bc456104bbf8155150e9366a241d7286d92d1d181f89'
files=json.loads(manifest)['files'];assert len(files)==41
assert sum(v['bytes'] for v in files.values())==5532156
for name,value in files.items():
    relative=Path(name);assert not relative.is_absolute() and '..' not in relative.parts
    assert not any(x in name.lower() for x in ('.db','.sqlite','.pyc','__pycache__','.pytest_cache','holdout'))
    path=root/relative;assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes();assert len(raw)==value['bytes'] and sha(raw)==value['sha256'],name

final=read(root/'final-source-map.json');assert len(final)==7
assert all(dict(bytes=len((repo/k).read_bytes()),sha256=sha((repo/k).read_bytes()))==v for k,v in final.items())
first=read(root/'input-before.json');last=read(root/'p2-recheck/input-before.json')
assert first==read(root/'input-after.json') and last==read(root/'p2-recheck/input-after.json')
changed={k for k in first if first[k]!=last[k]}
assert changed=={'src/sim2act/web/app.js','tests/local_record_apps_ui.cjs','tests/test_local_record_apps_ui.py'}
bridge=read(root/'batch-qualification-bridge.json')
assert set(bridge['changed_inputs'])==changed
for k in changed:
    assert bridge['changed_inputs'][k]==dict(first=first[k],final=last[k])
assert first['tests/test_local_record_history.py']==last['tests/test_local_record_history.py']
assert first['src/sim2act/api.py']==last['src/sim2act/api.py']
assert first['src/sim2act/local_record_apps.py']==last['src/sim2act/local_record_apps.py']
old=read(Path('/workspace/correction-known-stop-20261018/input-before.json'))
product_keys=[k for k in last if k.startswith('src/')]
assert len(product_keys)==138
assert old['src/sim2act/db.py']==last['src/sim2act/db.py']
assert all(dict(bytes=len((repo/k).read_bytes()),sha256=sha((repo/k).read_bytes()))==last[k] for k in product_keys)

allcases=[];runs=[]
for folder,wanted in [(root,2),(root/'p2-recheck',1)]:
    execution=read(folder/'execution.json')
    assert execution['returncode']==0 and execution['source_drift']==[] and execution['real_model_calls']==0
    cases=list(ET.fromstring((folder/'result.xml').read_bytes()).iter('testcase'))
    assert len(cases)==wanted and all(x.find('failure') is None and x.find('error') is None for x in cases)
    allcases.extend((x.attrib['classname'],x.attrib['name']) for x in cases)
    runs.append(dict(path=str(folder),exit=0,outer_seconds=execution['elapsed_seconds'],cases=[x.attrib for x in cases]))
assert len(allcases)==3 and len(set(allcases))==2

page_reviews=[]
for folder,count,request_count,fixture_revoke in [(root,24,52,False),(root/'p2-recheck',30,54,True)]:
    data=folder/'pytest-temp/test_local_record_page_explici0'
    page=read(data/'page-result.json');summary=read(data/'run-summary.json');info=read(data/'info.json')
    assert page['status']=='PASS' and len(page['checks'])==count
    assert len(page['actions'])==request_count and len(page['static_resource_loads'])==27 and page['boots']==1
    assert all(x['method']=='GET' for x in page['actions'])
    assert summary['status']=='PASS' and summary['page_worker_calls']==0 and summary['fixture_worker_calls']==1
    assert summary['actual_no_model_runs']==1 and summary['page_post_count']==0 and summary['real_model_requests']==0
    assert read(data/'worker-log.json')==[] and read(data/'source-changes.json')=={}
    assert read(data/'source-before.json')==read(data/'source-after.json')
    trace=read(data/'http-trace.json');cursor=0
    for action in page['actions']:
        match=next(n for n in range(cursor,len(trace)) if trace[n]['method']==action['method']
            and urlsplit(trace[n]['url']).path+('?' + urlsplit(trace[n]['url']).query if urlsplit(trace[n]['url']).query else '')==action['path']
            and trace[n]['status']==action['status'] and trace[n]['response']==action['response_text'])
        cursor=match+1
    mapping=read(folder/'input-before.json')
    for asset in page['static_resource_loads']:
        key='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
        assert asset['status']==200 and mapping[key]['sha256']==asset['sha256']
    generic=[x for x in page['actions'] if x['path']=='/api/runs/'+info['seed_run'] and x['status']==200]
    assert generic
    value=json.loads(generic[0]['response_text'])
    assert value['namespace']=='local-record-app.v1' and value['id']==info['seed_run']
    assert value['instance_id']==info['instance'] and value['app_id']==info['app']
    assert value['project_id']==info['project'] and value['release_id']==info['release']
    assert value['event']['title']==info['title_a'] and value['result_version']==1
    assert value['receipt']['status']=='VERIFIED'
    dedicated=[json.loads(x['response_text']) for x in page['actions']
        if x['path']==f"/api/internal/record-instances/{info['instance']}/runs/{info['seed_run']}" and x['status']==200]
    assert dedicated and any(x['event']==value['event'] and x['output']==value['output'] and x['receipt']==value['receipt'] for x in dedicated)
    details=dict(root=str(folder),checks=count,page_api_gets=request_count,assets=27,boots=1,
        page_posts=0,page_worker=0,fixture_no_model_worker=1,typed_run=info['seed_run'],app_id=info['app'],instance_id=info['instance'])
    if fixture_revoke:
        rev=read(data/'actual-revocation-proof.json');log=read(data/'fixture-revocation-log.json')
        assert rev['changed_tables']==['grants'] and len(log)==1 and rev['fixture_grant_mutations']==log
        before=log[0]['before'];after=log[0]['after']
        assert before['revoked'] is False and after['revoked'] is True and after['revision']==before['revision']+1
        assert {k:v for k,v in before.items() if k not in {'revoked','revision'}}=={k:v for k,v in after.items() if k not in {'revoked','revision'}}
        assert before['resource_id']==info['seed_artifact'] and before['tool_ref']=='resource.read'
        assert rev['only_exact_known_grant_changed'] and rev['all_other_rows_unchanged'] and rev['original_run_rows_unchanged']
        denied=[x for x in page['actions'] if x['path']=='/api/runs/'+info['seed_run'] and x['status']==403]
        assert len(denied)==1 and denied[0]['controlled_delivery']=='HELD_AFTER_ACTUAL_HTTP'
        assert json.loads(denied[0]['response_text'])['error']['code']=='GRANT_REVOKED'
        assert 'late actual permission denial cannot clear the current selection or paint an old error' in page['checks']
        details.update(p2='CLOSED_SOURCE_AND_ACTUAL_403_DELIVERY_CHECK',fixture_grant_revokes=1,
            full_table_claim='Executed snapshot oracle/FP only; no retained full-row exports to recompute independently')
    else:
        assert summary['all_rows_unchanged'] is True
        details.update(p2='NOT_COVERED_BEFORE_FIX',fixture_grant_revokes=0,
            full_table_claim='Executed 55-table equality oracle; no retained full-row exports')
    page_reviews.append(details)

app=(repo/'src/sim2act/web/app.js').read_text()
assert 'if(!current()||readWorkspace!==workspaceSelectionGeneration||readConnection!==identityConnectionGeneration)return;\n    clearRunDetail();activeRun=null;' in app
static=read(root/'static-checks.json')['checks']
assert all(x['exit']==0 for x in static)
result=dict(status='LIMITED_PASS_TYPED_LOCAL_RECORD_PROJECT_HISTORY_ENTRY',
    method='Source and closed-file audit; not independent product execution or DB read',
    author_manifest=dict(path=str(root/'sealed-manifest.json'),sha256=sha(manifest),files=41,raw_bytes=5532156,verified=files),
    current_final_source_files=final,product_entries=138,all_current_product_matches_final_input=True,
    legacy_db_source_unchanged=True,changed_inputs_between_batches=sorted(changed),
    api_qualification_bridge='First API PASS retained: backend/product Python/test dependencies identical; no API rerun claimed',
    runs=runs,unique_test_cases=2,test_case_executions=3,pass_executions=3,failures=0,page_reviews=page_reviews,
    p2=dict(original_finding='Late typed detail error lacked workspace/connection guard',
        fix='Catch checks both before any DOM or activeRun mutation; common current scope unchanged',
        source_review='CLOSED',actual_recheck='PASS held actual 403 across workspace ABA'),
    api_test_scope='Passed assertions cover owner typed GET, event/output equality, foreign owner/read revoke barriers, direct Store.inspect and generic-command legacy rejection; SQL/full-table evidence is executed assertions, not independently recomputed DB data',
    static_author_records=dict(count=len(static),all_pass=True,not_rerun=True),
    limits=['Both pages use one real NoModel CREATE fixture each; no page Worker/model/POST',
        'One final synthetic fixture Grant revoke is external to the page and adds no production permission capability',
        'No independent reconstruction of 54/55 full-table rows from DB or retained exports',
        'ASGI/TestClient served-page JSDOM only; not native/browser network, Windows, PG or semantic acceptance',
        'No Git/auth/network/private holdout, real models, future commit/push or full F2 qualification'])
(out/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','changed_inputs_between_batches','runs','unique_test_cases','test_case_executions','page_reviews','p2')},ensure_ascii=False,indent=2))
