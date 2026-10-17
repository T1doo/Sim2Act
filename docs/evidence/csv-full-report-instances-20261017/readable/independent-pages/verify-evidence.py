"""Read-only verification of already executed HTTP/UI/SQLite receipts."""
from pathlib import Path
import hashlib, io, json, sqlite3, subprocess, tarfile, xml.etree.ElementTree as ET

out=Path(__file__).parent
before=json.loads((out/'source-before.json').read_text())
snapshot=Path(before['snapshot'])
after={p:hashlib.sha256((snapshot/p).read_bytes()).hexdigest() for p in before['input_before_sha256']}
assert after==before['input_before_sha256']
archive=subprocess.check_output(['git','archive',before['source_sha'],*before['git_archive_paths']],cwd='/workspace/Sim2Act')
assert hashlib.sha256(archive).hexdigest()==before['git_archive_sha256']
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    original={m.name:hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar if m.isfile()}
assert original==after
(out/'source-after.json').write_text(json.dumps({'source_sha':before['source_sha'],'count':len(after),'all_inputs_unchanged_and_git_equal':True,'input_after_sha256':after},indent=2)+'\n')
pages={}
for p in sorted((out/'data').glob('*/page-result.json')):
    if p.parent.is_symlink(): continue
    info=json.loads((p.parent/'info.json').read_text());page=json.loads(p.read_text())
    assert info['case'] not in pages and page['status']=='PASS',(info,page.get('error'))
    pages[info['case']]=(p.parent,info,page)
assert set(pages)=={'lost','navigation'}
proof={'source_sha':before['source_sha'],'status':'PASS','inputs_unchanged':len(after),'cases':{},'http_errors':[]}
for case,(d,info,page) in pages.items():
    requests=page['requests'];raw=json.loads((d/'actual-http.json').read_text())
    for scope,items in [('page',requests),('all-http',raw)]:
        for i,r in enumerate(items):
            if r['status']>=400: proof['http_errors'].append({'case':case,'scope':scope,'index':i,'method':r['method'],'path':r['path'],'status':r['status'],'response':r.get('response')})
    for asset in page['assets']:
        name='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
        assert asset['sha256']==after[name]
    worker=json.loads((d/'page-worker-proof.json').read_text());assert worker['worker_runs']==[] and worker['real_model_requests']==0
    uses=[r for r in requests if r['method']=='POST' and r['path'].endswith('/csv-full-report-uses')]
    assert len(uses)==(1 if case=='lost' else 2)
    receipts=[]
    for sent in uses:
        reply=sent['response'];body=sent['body'];iid=sent['path'].split('/')[4]
        fp=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert sent['status']==202 and reply['instance_id']==iid and reply['request_key']==body['request_key']
        assert reply['request_fingerprint']==fp and reply['resource_id']==body['resource_id']
        assert reply['revision']==body['expected_revision'] and reply['release_fingerprint']==body['expected_release_fingerprint']
        assert reply['project_id']==info['project'] and reply['model_requests']==0
        assert not any(r['method']=='POST' and r['path']=='/api/runs/'+reply['run_id']+'/confirm-csv-report' for r in requests)
        receipts.append(reply)
    db=sqlite3.connect((d/'fixture.db').resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        stored=[]
        for receipt in receipts:
            job=dict(db.execute('SELECT id,status,result FROM runs WHERE id=?',(receipt['run_id'],)).fetchone())
            typed=dict(db.execute('SELECT id,instance_id,release_id,request_key,result_version FROM internal_app_runs WHERE id=?',(receipt['app_run_id'],)).fetchone())
            assert job['status']=='WAITING_APPROVAL' and job['result'] in (None,'null')
            assert typed['instance_id']==receipt['instance_id'] and typed['release_id']==receipt['release_id'] and typed['request_key']==receipt['request_key'] and typed['result_version'] is None
            stored.append({'ordinary':job,'typed':typed})
        counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ['operations','attempts','reservations','grants','principals','internal_run_bindings','internal_instance_data','internal_app_runs']}
        assert counts['operations']==3 and all(counts[k]==0 for k in ['attempts','reservations','internal_run_bindings','internal_instance_data'])
        assert counts['internal_app_runs']==len(receipts)
    finally: db.close()
    row={'checks':len(page['checks']),'page_requests':len(requests),'full_http_requests':len(raw),'asset_count':len(page['assets']),'all_asset_hashes_match_git':True,'receipts':receipts,'read_only_sqlite':{'stored':stored,'counts':counts},'new_use_worker_calls':0,'source_completed_with_original_NoModel_worker':True}
    if case=='lost':
        lost=[(i,r) for i,r in enumerate(requests) if r.get('delivery','').startswith('ACTUAL_')]
        assert [r['status'] for _,r in lost]==[201,200,201,202]
        stages=[]
        for i,sent in lost:
            assert sent['method']=='POST' and sum(r['method']=='POST' and r['path']==sent['path'] for r in requests)==1
            stage=sent['delivery'].split(':')[1]
            diagnostic=next(x for x in page['diagnostics']['losses'] if x['stage']==stage)
            following=next((j for j in range(i+1,len(requests)) if requests[j]['method']=='POST'),len(requests))
            segment=requests[i+1:following]
            assert segment and all(r['method']=='GET' and r['status']==200 for r in segment)
            exact=[(j,r) for j,r in enumerate(requests[i+1:following],i+1) if r['path']==diagnostic['expected_get']]
            assert exact
            stages.append({'stage':stage,'accepted_status':sent['status'],'post_index':i,'next_explicit_post_index':following,'post_count_for_path':1,'original_body':sent['body'],'exact_get_path':diagnostic['expected_get'],'exact_get_indices':[j for j,_ in exact],'all_requests_until_next_explicit_post_are_get200':True})
        assert len([r for r in requests if r['method']=='POST'])==5
        row['four_actual_loss_recoveries']=stages
    else:
        a,b=uses
        assert a['body']['resource_id']!=b['body']['resource_id'] and a['body']['request_key']!=b['body']['request_key']
        assert a['response']['instance_id']!=b['response']['instance_id'] and a['response']['run_id']!=b['response']['run_id']
        for sent in uses:
            receipt_path='/api/internal/instances/'+sent['response']['instance_id']+'/csv-full-report-requests/'+sent['body']['request_key']
            assert not any(r['method']=='GET' and r['path']==receipt_path for r in requests)
        required=['late material callback cannot install inputs into another selected instance','late actual accepted instance Run cannot populate another project','late accepted new instance Run cannot populate another account','pending instance authorization exposes neither old workflow history nor its open control']
        assert all(label in page['checks'] for label in required)
        row['independent_scopes_and_no_late_receipt_get']=True
        row['page_navigation_assertions']=required
    proof['cases'][case]=row
assert not proof['http_errors'],proof['http_errors']
cases=ET.parse(out/'junit.xml').findall('.//testcase')
assert len(cases)==2 and all(not any(c.find(tag) is not None for tag in ['failure','error','skipped']) for c in cases)
proof['junit']={'unique_cases':2,'pytestcase_calls':2,'passed':2,'failures':0,'errors':0,'skipped':0,'cases':[c.attrib for c in cases]}
proof['limitations']=['synthetic SQLite/ASGI/TestClient/full-product-DOM JSDOM only','original source NoModel Worker ran in each fixture; no new instance-use Worker call, confirmation or MD download','deliver, adoption and new-report Worker/download are parent-run scope, not these two independent cases','no native browser/PostgreSQL/real model/Windows/remote CI; no process restart or ABA claim']
(out/'independent-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':proof['status'],'junit':proof['junit'],'cases':{k:{f:v[f] for f in ['checks','page_requests','full_http_requests','asset_count']} for k,v in proof['cases'].items()},'http_errors':proof['http_errors'],'source_inputs':len(after)},ensure_ascii=False,indent=2))
