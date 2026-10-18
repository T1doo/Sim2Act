"""Independent stdlib-only review of closed files; no product imports or IO calls."""
import datetime,hashlib,json,math,re
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

root=Path('/workspace/local-record-controls-20261018')
out=Path('/workspace/local-record-controls-review-20261018')
repo=Path('/workspace/Sim2Act')
case=root/'pytest-temp/test_local_record_page_explici0'
def load(path): return json.loads(path.read_text())
def sha(raw): return hashlib.sha256(raw).hexdigest()
def fp(value): return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
manifest=(root/'sealed-manifest.json').read_bytes()
assert sha(manifest)=='a7dbb093ef3fd825ed5898d61c53105f7e965f134d16fcbd1a8bfb3202822c9e'
entries=json.loads(manifest)['files']
if isinstance(entries,list): entries={x['path']:{k:v for k,v in x.items() if k!='path'} for x in entries}
assert len(entries)==34 and sum(v['bytes'] for v in entries.values())==5100456
for name,value in entries.items():
    p=Path(name);assert not p.is_absolute() and '..' not in p.parts
    assert not any(s in name.lower() for s in ('.db','.sqlite','.pyc','__pycache__','.pytest_cache','holdout'))
    path=root/p;assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes();assert len(raw)==value['bytes'] and sha(raw)==value['sha256'],name

execution=load(root/'execution.json');page=load(case/'page-result.json');info=load(case/'info.json')
assert execution['returncode']==1 and execution['source_drift']==[] and execution['real_model_calls']==0
assert page['status']=='PASS' and len(page['checks'])==22 and len(page['actions'])==39
assert len(page['static_resource_loads'])==54 and page['boots']==2
assert load(case/'run-summary.json')['status']=='NOT_COMPLETED'
assert load(case/'worker-log.json')==[] and load(case/'source-changes.json')=={}
before_inputs=load(root/'input-before.json');assert before_inputs==load(root/'input-after.json')
assert load(case/'source-before.json')==load(case/'source-after.json')
final=load(root/'final-source-map.json');assert len(final)==4
assert all(dict(bytes=len((repo/p).read_bytes()),sha256=sha((repo/p).read_bytes()))==v for p,v in final.items())
for p in ('src/sim2act/web/local-records.js','tests/local_record_apps_ui.cjs'): assert final[p]==before_inputs[p]
bridge=load(root/'qualification-bridge.json')
assert bridge['actual_product_and_cjs_unchanged'] and bridge['fresh_corrected_wrapper']=='NOT_RERUN'

posts=[x for x in page['actions'] if x['method']=='POST'];gets=[x for x in page['actions'] if x['method']=='GET']
rid=info['seed_run'];iid=info['instance'];path=f'/api/internal/record-instances/{iid}/runs/{rid}/commands'
assert len(posts)==3 and len(gets)==36
expected=[('pause',1,'PAUSED'),('resume',2,'QUEUED'),('cancel',3,'CANCELLED')]
for item,(command,version,status) in zip(posts,expected):
    assert item['path']==path and item['status']==200 and item['body']==dict(command=command,version=version)
    value=json.loads(item['response_text'])
    assert set(value)=={'namespace','id','status','version','content_access','formal_publication_enabled'}
    assert value==dict(namespace='local-record-app.v1',id=rid,status=status,version=version+1,content_access=False,formal_publication_enabled=False)
assert posts[1]['controlled_delivery']=='HELD_AFTER_ACTUAL_HTTP'
assert posts[2]['controlled_delivery']=='RECEIPT_LOST_AFTER_ACTUAL_HTTP'
assert any('newer empty instance' in s for s in page['checks'])
assert any('cold page retains' in s for s in page['checks'])
trace=load(case/'http-trace.json');cursor=0
for action in page['actions']:
    n=next(n for n in range(cursor,len(trace)) if trace[n]['method']==action['method']
        and urlsplit(trace[n]['url']).path+('?' + urlsplit(trace[n]['url']).query if urlsplit(trace[n]['url']).query else '')==action['path']
        and trace[n]['status']==action['status'] and trace[n]['response']==action['response_text'])
    cursor=n+1
for asset in page['static_resource_loads']:
    p='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
    assert asset['status']==200 and asset['sha256']==before_inputs[p]['sha256']
reads=[json.loads(x['response_text']) for x in gets if x['path']==path.removesuffix('/commands') and x['status']==200]
assert any(x['status']=='QUEUED' and x['version']==1 for x in reads)
assert any(x['status']=='QUEUED' and x['version']==3 for x in reads)
assert sum(x['status']=='CANCELLED' and x['version']==4 for x in reads)>=2

before=load(case/'database-before-page.json');after=load(case/'database-after-page.json')
assert len(before)==55 and before.keys()==after.keys()
mutable={'runs','internal_app_runs','events','heartbeats'}
assert {k for k in before if before[k]!=after[k]}==mutable
assert all(before[k]==after[k] for k in before if k not in mutable)
assert len(before['runs'])==len(after['runs']) and len(before['internal_app_runs'])==len(after['internal_app_runs'])
original=next(x for x in before['runs'] if x['id']==rid)
assert original['status']=='QUEUED' and original['version']==1
assert {x['id']:x for x in after['runs']}=={x['id']:({**x,'status':'CANCELLED','version':4,'cancel_intent':True} if x['id']==rid else x) for x in before['runs']}
aid=next(x['app_run_id'] for x in before['internal_run_bindings'] if x['run_id']==rid)
assert {x['id']:x for x in after['internal_app_runs']}=={x['id']:({**x,'status':'CANCELLED'} if x['id']==aid else x) for x in before['internal_app_runs']}
assert all(x in after['events'] for x in before['events'])
added=[x for x in after['events'] if x not in before['events']]
assert len(added)==3 and all(x['kind']=='COMMAND' and x['run_id']==rid and set(x['data'])=={'command','status'} for x in added)
assert sorted((x['data']['command'],x['data']['status']) for x in added)==sorted((a,c) for a,b,c in expected)
assert all(x in after['heartbeats'] for x in before['heartbeats'])
new_hb=[x for x in after['heartbeats'] if x not in before['heartbeats']]
assert len(new_hb)==1;hb=new_hb[0]
assert set(hb)=={'id','at'} and re.fullmatch('worker_[a-f0-9]{32}',hb['id'])
assert type(hb['at']) in (int,float) and math.isfinite(hb['at'])
bounds=[datetime.datetime.fromisoformat(execution[k]).timestamp() for k in ('started_at','ended_at')]
assert bounds[0]<=hb['at']<=bounds[1] and max(x['created_at'] for x in added)<=hb['at']
proof=load(root/'oracle-correction/closed-snapshot-proof.json')
assert proof['database_before_fingerprint']==fp(before) and proof['database_after_fingerprint']==fp(after)
assert proof['probe_worker_id_captured'] is False and proof['probe_id_independently_captured'] is False
assert proof['other_tables_unchanged']==51 and proof['probe_heartbeat']==hb
assert before['internal_instance_data']==after['internal_instance_data']==[]
assert before['attempts']==after['attempts']==[]

original_cases=list(ET.fromstring((root/'result.xml').read_bytes()).iter('testcase'))
oracle_cases=list(ET.fromstring((root/'oracle-correction/result.xml').read_bytes()).iter('testcase'))
assert len(original_cases)==1 and original_cases[0].find('failure') is not None
assert len(oracle_cases)==1 and oracle_cases[0].find('failure') is None and oracle_cases[0].find('error') is None
correction_execution=load(root/'oracle-correction/execution.json')
static=load(root/'static-checks.json')
checks=static['checks'] if isinstance(static,dict) else static
assert all(x.get('exit',x.get('returncode'))==0 for x in checks)
result=dict(status='LIMITED_PASS_PAGE_AND_CLOSED_JSON_CONTRACT_ORIGINAL_WRAPPER_FAIL_RETAINED',
    author_manifest=dict(path=str(root/'sealed-manifest.json'),sha256=sha(manifest),files=len(entries),raw_bytes=sum(v['bytes'] for v in entries.values()),verified=entries),
    actual=dict(pytest='FAIL_RETAINED_HEARTBEAT_ORACLE',outer_seconds=execution['elapsed_seconds'],
        testcase=original_cases[0].attrib,page='PASS',checks=22,frontend_gets=36,frontend_posts=3,assets=54,boots=2,
        run=rid,instance=iid,model_calls=0,business_worker_claims=0,worker_once_probe=1,
        probe_result='False assertion reached before failed snapshot assertion'),
    post_failure=dict(pure_json_pytest='PASS',testcase=oracle_cases[0].attrib,execution=correction_execution,
        fresh_corrected_product_wrapper='NOT_RERUN',product_and_cjs_bytes_unchanged=True,
        final_four_files=final),
    independently_recomputed_export=dict(tables=55,unchanged_tables=51,changed_tables=sorted(mutable),
        run='Only original Run status/version/cancel intent changed',app_run='Only original AppRun status changed',
        command_events=3,unique_new_heartbeat=hb,heartbeat_id_separately_captured=False,
        physical_database='NOT_READ_OR_HASHED',before_fingerprint=fp(before),after_fingerprint=fp(after)),
    control_contract=dict(command_sequence=expected,strict_six_field_receipts=True,
        same_scope_versions=[1,2,3,4],held_resume=True,lost_cancel_receipt=True,
        explicit_get_recovery=True,cold_terminal_read_without_resend=True),
    static_author_checks=dict(count=len(checks),all_exit_zero=True,not_rerun=True),
    reviewer_execution='Stdlib-only files/JSON audit; no product import, SQL/DB, network, Git, Worker, model or holdout',
    limits=['Original run-summary remains NOT_COMPLETED and original pytest FAIL is not reclassified',
        'The pure JSON checker is not another functional/product testcase or API/Worker execution',
        'Final corrected future wrapper and captured future probe identity were not exercised',
        'UNKNOWN same-version, known4xx, RUNNING, revoke/lease/crash and other matrices not executed here',
        'No real model/LIVE, native Windows/browser, PG, semantics, CI or future commit/push qualification'])
(out/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','actual','post_failure','independently_recomputed_export','control_contract')},ensure_ascii=False,indent=2))
