"""Pure-file audit: no application imports, DB, product, subprocess or network."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path('/workspace/correction-known-stop-20261018')
out=Path('/workspace/correction-known-stop-review-20261018')
repo=Path('/workspace/Sim2Act')
def load(name): return json.loads((root/name).read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
manifest_bytes=(root/'sealed-manifest.json').read_bytes()
assert sha(manifest_bytes)=='fa010eb80292f6dc775b171f835f4a1d0779be3c2670251ee4be78ca2135acfa'
entries=json.loads(manifest_bytes)['files']
assert len(entries)==26 and sum(x['bytes'] for x in entries)==3245125
verified=[]
for item in entries:
    relative=Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert not any(x in item['path'].lower() for x in ('.db','.sqlite','holdout'))
    path=root/relative
    assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],item['path']
    verified.append(item)

before_inputs=load('input-before.json')
assert before_inputs==load('input-after.json')
final_inputs=load('final-source-map.json')
assert all(dict(bytes=len((repo/path).read_bytes()),sha256=sha((repo/path).read_bytes()))==entry
    for path,entry in final_inputs.items())
for path,artifact in [('src/sim2act/web/internal.js','executed-internal.js'),
    ('src/sim2act/web/owner-review.js','executed-owner-review.js'),
    ('tests/natural_spec_corrections_ui.cjs','executed-natural_spec_corrections_ui.cjs')]:
    raw=(root/artifact).read_bytes()
    assert dict(bytes=len(raw),sha256=sha(raw))==before_inputs[path]
observer=json.loads((out/'observer-static-review.json').read_text())
final_internal=(repo/'src/sim2act/web/internal.js').read_bytes()
block=observer['only_removed_block'].encode()
assert final_internal.count(block)==1
assert final_internal.replace(block,b'',1)==(root/'executed-internal.js').read_bytes()
product_keys=[k for k in before_inputs if k.startswith('src/')]
assert len(product_keys)==138
assert all(dict(bytes=len((repo/k).read_bytes()),sha256=sha((repo/k).read_bytes()))==before_inputs[k]
    for k in product_keys if k!='src/sim2act/web/internal.js')

execution=load('execution.json');page=load('page-result.json');proof=load('cancelled-child-proof.json')
assert execution['status']=='PASS' and execution['error'] is None and execution['node_returncode']==0
assert execution['source_drift']==[] and execution['parent_model_calls']==1
assert execution['child_model_calls']==0 and execution['real_model_requests']==0
assert page['status']=='PASS' and page['error'] is None
assert len(page['checks'])==10 and len(page['actions'])==11 and len(page['requests'])==43
assert len(page['static_resource_loads'])==27 and page['boots']==1
child=execution['child']
assert child=='run_e912cc36f5694cb5a8af2b90e782b351'
assert proof['header']==dict(id=child,status='CANCELLED',cancel_intent=True)
assert proof['child_attempts']==0 and proof['post_cancel_worker_claimed'] is False
assert proof['post_cancel_model_calls']==0 and proof['typed_rows_unchanged'] is True

http=[json.loads(line) for line in (root/'http.ndjson').read_text().splitlines()]
assert len(http)==len(page['requests'])
for logged,recorded in zip(http,page['requests']):
    assert all(logged['request'].get(k)==recorded.get(k) for k in ('method','path','body','headers'))
posts=[x for x in http if x['request']['method']=='POST']
assert len(posts)==3
assert sum(x['request']['path'].endswith('/correction-reviews') for x in posts)==1
assert sum(x['request']['path'].endswith('/correction-runs') for x in posts)==1
cancel=next(x for x in posts if x['request']['path'].endswith('/runs/'+child+'/commands'))
assert cancel['request']['body']==dict(command='cancel',version=1)
assert cancel['response']['status']==200 and json.loads(cancel['response']['text'])['status']=='CANCELLED'
control=[x for x in http if x['request']['path'].endswith('/runs/'+child+'/control-status')]
assert len(control)==2 and all(x['request']['method']=='GET' and x['response']['status']==200 for x in control)
states=[json.loads(x['response']['text']) for x in control]
assert [(x['status'],x['version'],x['cancel_intent']) for x in states]==[('QUEUED',1,False),('CANCELLED',2,True)]
assert all(x['id']==child and x['content_access'] is False and x['formal_publication_enabled'] is False
    and x['namespace']=='INTERNAL_ENGINEERING_ONLY' for x in states)
denied=[x for x in http if x['response']['status']==403]
assert len(denied)==1 and denied[0]['request']['path'].endswith('/instances/'+states[0]['instance_id'])
assert json.loads(denied[0]['response']['text'])['error']['code']=='GRANT_REVOKED'
order=[http.index(denied[0]),http.index(control[0]),http.index(cancel),http.index(control[1])]
assert order==sorted(order)
for asset in page['static_resource_loads']:
    path='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
    assert asset['status']==200 and asset['sha256']==before_inputs[path]['sha256']

parent=load('parent-worker-proof.json')
assert len(parent['wire'])==1 and len(parent['claims'])==1 and parent['claims'][0]['claimed'] is True
assert parent['claims'][0]['after']['status']=='SUCCEEDED'
revocations=load('revocation.json');assert len(revocations)==1
revocation=revocations[0]
assert revocation['child']==child and revocation['grant']['tool_ref']=='resource.read'
assert revocation['response']==dict(status='REVOKED')
before=load('database-before-page.json');after=load('database-after-page.json')
assert len(before)==55 and set(before)==set(after)
assert before['internal_instance_data']==after['internal_instance_data']
assert not any(x['run_id']==child for x in after['attempts'])
child_row=next(x for x in after['runs'] if x['id']==child)
assert child_row['status']=='CANCELLED' and child_row['cancel_intent'] is True
parent_row=next(x for x in before['runs'] if x['id']==parent['run'])
assert parent_row in after['runs']
grant_id=revocation['grant']['id']
oldgrant=next(x for x in before['grants'] if x['id']==grant_id)
newgrant=next(x for x in after['grants'] if x['id']==grant_id)
assert oldgrant['revoked'] is False and newgrant['revoked'] is True
assert newgrant['revision']==oldgrant['revision']+1
assert {k:v for k,v in oldgrant.items() if k not in {'revoked','revision'}}=={k:v for k,v in newgrant.items() if k not in {'revoked','revision'}}
assert [x for x in before['grants'] if x['id']!=grant_id]==[x for x in after['grants'] if x['id']!=grant_id]
for table in ('natural_owner_records','natural_owner_seals','internal_instance_data','resources','local_effects','operations'):
    assert before[table]==after[table]

synthetic=load('synthetic-final.json');initial=load('synthetic-first.json')
assert synthetic['status']=='PASS' and len(synthetic['checks'])==30
assert initial['status']=='PASS' and len(initial['checks'])==29
assert synthetic['classification']=='ACTUAL_PAGE_CONTROLLERS_SYNTHESIZED_NAVIGATION_AND_CANCEL'
assert 'workspace return visibly invalidates old stop controls' in synthetic['checks']
unit=load('unit-temp/test_verified_correction_run_e0/correction-run-entry.json')
assert unit['status']=='PASS' and len(unit['checks'])==30 and unit['checks']==synthetic['checks']
for result in (synthetic,unit):
    for name,digest in result['assets'].items():
        assert sha((repo/'src/sim2act/web'/name).read_bytes())==digest
suite=ET.fromstring((root/'unit.xml').read_bytes());cases=list(suite.iter('testcase'))
assert len(cases)==1 and cases[0].find('failure') is None and cases[0].find('error') is None
static=load('static-checks.json');assert len(static)==6 and all(x['returncode']==0 for x in static)

result=dict(status='LIMITED_PASS_KNOWN_CORRECTION_STOP_ENTRY',method='Independent source and closed-file review; no product execution or DB read',
    author_manifest=dict(path=str(root/'sealed-manifest.json'),sha256=sha(manifest_bytes),files=26,raw_bytes=3245125,verified=verified),
    execution_inputs=dict(entries=len(before_inputs),product_entries=138,before_after_equal=True,
        post_actual_product_change='Only exact 413-byte stale-panel observer; removed block restores executed internal.js bytes',
        final_five_paths_match_current=True),
    actual=dict(status='PASS',seconds=execution['elapsed_seconds'],pytest=False,
        checks=10,gestures=11,page_api_requests=43,page_post_requests=3,page_assets=27,
        child=child,parent=parent['run'],parent_mock=1,parent_claims=1,child_mock=0,child_attempts=0,
        post_cancel_worker_claimed=False,typed_exports_unchanged=True,real_model_requests=0,
        flow=['Explicit material READ revoke','Instance 403 GRANT_REVOKED','Metadata QUEUED/version1',
            'Explicit cancel(version1) POST200','Metadata CANCELLED/version2/cancel_intent=true']),
    synthetic=dict(final_checks=30,first_checks=29,unit_wrapper_cases=1,unit_wrapper_status='PASS',
        unit_wrapper_seconds=cases[0].attrib.get('time'),classification=synthetic['classification'],
        accounting='The wrapper repeats the same final synthetic checks, not another unique functional matrix'),
    snapshot_exports=dict(tables=55,source='Author JSON exports, not a direct database read',
        changed_tables=[dict(table=k,before=len(before[k]),after=len(after[k])) for k in before if before[k]!=after[k]],
        material_read_grant='One exact existing Grant revoked, revision advanced; all other Grants equal',
        no_new_typed_rows=True,no_child_attempt=True),
    static_author_records=dict(count=6,all_returncode_zero=True,not_rerun_by_reviewer=True),
    limitations=['Existing synthetic database was copied, then a normal new parent Run was created; no fresh gen3 chain is claimed',
        'The actual case preceded the observer; only the synthetic workspace invalidation check exercised that final addition',
        'Predicted unordered typed comparison risk did not occur; actual wrapper genuinely PASS',
        'No successful real-model or LIVE/production-source qualification, Windows/native, PG, CI or future push is inferred',
        'Physical DB contents/hashes, Git/auth/network and private holdouts were not accessed'])
(out/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','execution_inputs','actual','synthetic','snapshot_exports')},ensure_ascii=False,indent=2))
