"""Independent read-only assertions over this run's raw receipts, not new tests."""
from pathlib import Path
import collections, hashlib, io, json, sqlite3, subprocess, tarfile, xml.etree.ElementTree as ET

out=Path(__file__).parent
source=json.loads((out/'source-before.json').read_text())
snapshot=Path(source['snapshot'])
after={p:hashlib.sha256((snapshot/p).read_bytes()).hexdigest() for p in source['input_before_sha256']}
assert after==source['input_before_sha256']
archive=subprocess.check_output(['git','archive',source['source_sha'],*source['git_archive_paths']],cwd='/workspace/Sim2Act')
assert hashlib.sha256(archive).hexdigest()==source['git_archive_sha256']
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    git_after={m.name:hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar if m.isfile()}
assert git_after==after
(out/'source-after.json').write_text(json.dumps({'source_sha':source['source_sha'],'input_count':len(after),'all_inputs_unchanged':True,'git_archive_rechecked_all_equal':True,'input_after_sha256':after},indent=2)+'\n')
pages={}
for p in sorted((out/'data').glob('*/page-result.json')):
    if p.parent.is_symlink(): continue
    info=json.loads((p.parent/'info.json').read_text())
    page=json.loads(p.read_text())
    assert info['case'] not in pages
    pages[info['case']]=(p.parent,info,page)
assert set(pages)=={'same-navigation','next-unknown','navigation'},set(pages)

http_errors=[]; asset_rows=[]; deliveries=[]
for case,(d,info,page) in pages.items():
    assert page['status']=='PASS',(case,page.get('error'))
    raw=json.loads((d/'actual-http.json').read_text())
    for scope,requests in [('full-actual-http',raw),('page',page['requests'])]:
        for i,r in enumerate(requests):
            if r['status']>=400: http_errors.append({'case':case,'scope':scope,'index':i,'method':r['method'],'path':r['path'],'status':r['status'],'response':r.get('response')})
    for asset in page['assets']:
        rel='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
        assert rel in after,(case,rel)
        assert asset['sha256']==after[rel],(case,asset)
    asset_rows.append({'case':case,'count':len(page['assets']),'all_match_git_source':True,'assets':page['assets']})
    req=page['requests']; base='/api/internal/instances/'+info['instance']+'/csv-goal-revisions'
    previews=[r for r in req if r['method']=='POST' and r['path']==base+'/previews']
    assert len(previews)==1 and previews[0]['status']==201
    preview=previews[0]['response']; context=preview['context']; key=preview['request_key']
    assert preview['spec_revision']==3 and context['parent']['spec_revision']==2
    assert context['parent']['release_id']==info['release'] and context['parent']['column']=='quantity'
    assert preview['baseline_input']['column']=='quantity' and preview['input']['column']=='amount'
    assert not any(r['method']=='POST' and r['path'].endswith('/delivery-graph/derive') for r in req[:req.index(previews[0])+1])
    if case!='navigation':
        assert not any(r['method']=='POST' and r['path'].endswith('/delivery-graph/derive') for r in req)
    expected_goal=3 if case=='next-unknown' else 2
    assert context['goal']['version']==expected_goal
    assert context['goal_mode']==('EXPLICIT_NEXT_GOAL' if expected_goal==3 else 'KEEP_ADOPTED_GOAL')
    puts=[r for r in req if r['method']=='PUT' and r['path'].startswith('/api/goal-cards/')]
    assert len(puts)==(1 if expected_goal==3 else 0)
    checks=[r for r in req if r['method']=='POST' and r['path']==base+'/checks']
    assert len(checks)==1 and checks[0]['status']==202
    assert checks[0]['body']['request_key']==key
    if case=='navigation':
        # Navigation deliberately selects an original-root second instance. Its
        # explicit baseline action may use the pre-existing root derive route.
        assert all(r['path'].endswith('/delivery-graph/derive') for r in req[req.index(checks[0])+1:] if r['method']=='POST')
        assert not (d/'actual-browser-delivery.json').exists()
        continue
    proof=json.loads((d/'actual-browser-delivery.json').read_text())
    new=proof['new']; instance=proof['instance']; contract=proof['contract']
    assert new['result']['sum']=='30' and isinstance(new['result']['sum'],str)
    assert new['result_version']==3 and new['instance_id']==info['instance']
    assert new['known_effects'][0]['run_id']==new['app_run_id']
    assert new['release_id']!=info['release'] and instance['release_id']==new['release_id']
    assert instance['revision']==3 and instance['data_version']==3
    assert contract['goal']['goal']==context['goal']['snapshot']['content']['goal']
    owner_path='/api/internal/instances/'+info['instance']+'/runs/'+new['id']+'/csv-owner-review'
    owner=[r for r in req if r['method']=='GET' and r['path']==owner_path]
    assert owner and owner[-1]['status']==200 and owner[-1]['response']['owner_acceptance']=='PENDING'
    con=sqlite3.connect((d/'fixture.db').resolve().as_uri()+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    try:
        final_counts={table:con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('grants','principals')}
        assert final_counts==proof['unchanged_counts']
        stored=[dict(r) for r in con.execute('SELECT id,release_id,input,status,output,result_version FROM internal_app_runs WHERE instance_id=? ORDER BY result_version',(info['instance'],))]
        assert [r['result_version'] for r in stored]==[1,2,3]
        assert [json.loads(r['output'])['sum'] for r in stored]==['30','5','30']
        assert [json.loads(r['input'])['column'] for r in stored]==['amount','quantity','amount']
        assert all(r['status']=='SUCCEEDED' for r in stored)
        assert stored[-1]['id']==new['app_run_id'] and len({r['id'] for r in stored})==3
        assert len({r['release_id'] for r in stored})==3
    finally:
        con.close()
    deliveries.append({'case':case,'new_run':new['id'],'app_run_id':new['app_run_id'],'instance_id':info['instance'],'release_id':new['release_id'],'result_version':new['result_version'],'sum':new['result']['sum'],'goal_version':expected_goal,'owner_acceptance':'PENDING','new_store_reopen_inspect':True,'process_restart':False,'unchanged_counts':proof['unchanged_counts'],'read_only_final_sqlite_counts':final_counts,'stored_business_versions':stored})

def exact_read(segment,path):
    rows=[r for r in segment if r['path']==path]
    assert len(rows)==1,(path,len(rows))
    assert rows[0]['method']=='GET' and rows[0]['status']==200
    return rows[0]['response']

d,info,page=pages['same-navigation']; req=page['requests']
base='/api/internal/instances/'+info['instance']+'/csv-goal-revisions'
preview=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/previews'); key=preview['request_key']
return_rows=[]
for stage,suffix in [('preview','/previews'),('release','/version-approvals'),('adoption','/adoption-approvals')]:
    posted=next(i for i,r in enumerate(req) if r['method']=='POST' and r['path']==base+suffix)
    following=next(i for i in range(posted+1,len(req)) if req[i]['method']=='POST')
    start=next(i for i in range(posted+1,following) if req[i]['method']=='GET' and req[i]['path']==base+'/context')
    assert all(r['method']=='GET' and r['status']==200 for r in req[start:following])
    segment=req[start:following]
    assert not any(r['method']=='POST' for r in req[posted+1:following])
    assert exact_read(segment,base+'/context')==preview['context']
    assert exact_read(segment,base+'/previews/'+key)==preview
    accepted=req[posted]['response']
    if stage in ('release','adoption'):
        checked=exact_read(segment,base+'/checks/'+key)
        assert checked['status']=='PASS' and checked['request_key']==key
        approved=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/version-approvals')
        assert exact_read(segment,base+'/version-approvals/'+key)==approved
        live=exact_read(segment,'/api/internal/approvals/'+approved['id'])
        assert live['fingerprint']==approved['fingerprint'] and live['payload']['snapshot']==approved['snapshot']
        assert approved['snapshot']['csv_goal_revision_source']['check_fingerprint']==checked['check_fingerprint']
    if stage=='adoption':
        saved=exact_read(segment,base+'/adoption-approvals/'+key)
        assert saved['id']==accepted['id'] and saved['fingerprint']==accepted['fingerprint']
        original=next(r['response'] for r in req[posted+1:start] if r['method']=='GET' and r['path']==base+'/adoption-approvals/'+key)
        assert saved==original
        release=exact_read(segment,'/api/internal/releases/'+saved['payload']['target_release_id'])
        assert release['approval_id']==approved['id'] and release['fingerprint']==saved['payload']['target_fingerprint']
        assert req[following]['path']=='/api/internal/instances/'+info['instance']+'/switch-approvals/'+saved['id']+'/commit'
        assert req[following]['body']=={'fingerprint':saved['fingerprint']}
    elif stage=='release':
        assert req[following]['path']=='/api/internal/approvals/'+accepted['id']+'/commit'
        assert req[following]['body']=={'fingerprint':accepted['fingerprint']}
    else:
        assert req[following]['path']==base+'/checks'
        assert req[following]['body']['request_key']==key and req[following]['body']['expected_preview_fingerprint']==preview['preview_fingerprint']
    assert any(c==stage+' requires fresh visible consent' for c in page['checks'])
    assert any(c==stage+' return displays complete exact server-frozen payload' for c in page['checks'])
    return_rows.append({'stage':stage,'accepted_post_index':posted,'fresh_context_index':start,'next_explicit_post_index':following,'zero_post_between':True,'fresh_gets':segment,'page_exact_frozen_payload_and_new_consent_assertions':True})

d,info,page=pages['next-unknown']; req=page['requests']
base='/api/internal/instances/'+info['instance']+'/csv-goal-revisions'
preview=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/previews'); key=preview['request_key']
loss_rows=[]
for marker,status in [('ACTUAL_202_LOST',202),('ACTUAL_RELEASE_200_LOST',200),('ACTUAL_CAS_200_LOST',200)]:
    lost=[(i,r) for i,r in enumerate(req) if r.get('delivery')==marker]
    assert len(lost)==1
    index,sent=lost[0]; assert sent['method']=='POST' and sent['status']==status
    assert sum(r['method']=='POST' and r['path']==sent['path'] for r in req)==1
    following=next(i for i in range(index+1,len(req)) if req[i]['method']=='POST')
    recovery=req[index+1:following]
    assert recovery and all(r['method']=='GET' and r['status']==200 for r in recovery)
    if marker=='ACTUAL_202_LOST':
        saved=[r for r in recovery if r['path']==base+'/checks/'+key]
        assert saved and all(r['response']['request_key']==key and r['response']['run_id']==sent['response']['run_id'] for r in saved)
    elif marker=='ACTUAL_RELEASE_200_LOST':
        approved=next(r['response'] for r in req if r['method']=='POST' and r['path']==base+'/version-approvals')
        saved=[r for r in recovery if r['path']=='/api/internal/apps/'+info['app']+'/releases']
        assert saved and any(x['approval_id']==approved['id'] for r in saved for x in r['response']['items'])
    else:
        adoption=next(r['response'] for r in req if r['method']=='GET' and r['path']==base+'/adoption-approvals/'+key)
        a=adoption['payload']; saved=[r['response'] for r in recovery if r['path']=='/api/internal/instances/'+info['instance']]
        assert saved
        for instance in saved:
            assert instance['id']==info['instance'] and instance['project_id']==info['project'] and instance['source_app_id']==info['app']
            assert instance['principal_id']==adoption['principal_id'] and instance['runtime_id']==preview['context']['runtime_id']
            assert instance['release_id']==a['target_release_id'] and instance['release_fingerprint']==a['target_fingerprint']
            assert instance['revision']==preview['context']['instance_revision']+1 and instance['data_version']==preview['context']['data_version']
            assert any(h['kind']=='switch' and h.get('approval_id')==adoption['id'] and h.get('previous_release_id')==info['release'] and h.get('release_id')==a['target_release_id'] and h.get('revision')==3 for h in instance['history'])
    loss_rows.append({'delivery':marker,'post_index':index,'next_explicit_post_index':following,'actual_status':status,'post_count':1,'recovery_only_get_200':True,'original_request_key':key,'recovery':recovery})

tree=ET.parse(out/'junit.xml'); cases=tree.findall('.//testcase')
summary={'unique_cases':len(cases),'pytestcase_calls':len(cases),'passed':sum(not any(c.find(k) is not None for k in ('failure','error','skipped')) for c in cases),'failures':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'junit_tests':[{**c.attrib} for c in cases]}
assert summary['unique_cases']==3 and summary['passed']==3
result={'status':'PASS','source_sha':source['source_sha'],'source_inputs':len(after),'all_inputs_unchanged':True,'junit':summary,'assets':asset_rows,'strict_fresh_return_get_sequences':return_rows,'strict_lost_receipt_recovery':loss_rows,'completed_deliveries':deliveries,'http_error_responses':http_errors,'page_counts':{case:len(page['checks']) for case,(_,_,page) in pages.items()},'limitations':['synthetic SQLite/TestClient/NoModel Worker/JSDOM only','Store reopened with separate engine; no process restart','no native browser, PostgreSQL, real model, Windows or remote CI','navigation away with late callbacks; no ABA round-trip-before-callback assertion','v3 delivery proven; further revision button visibility only, no v4 run']}
(out/'independent-proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','source_sha','source_inputs','junit','page_counts','http_error_responses')},ensure_ascii=False,indent=2))
