"""Independent actual SQLite/API request metadata and stop/current-auth probes."""
import json,os
from pathlib import Path
import pytest
from sqlalchemy import select,update
from test_registered_text_recovery import ready,close_body,prepare_body
from test_registered_text_extraction import snapshot
from sim2act.db import registered_extraction_requests as journal
from sql_private_barrier import PrivateReadBarrier

OUT=Path('/tmp/pb-cold-recovery-review-20261011')
@pytest.mark.parametrize('fault',['instance','source-app'])
def test_project_discovery_does_not_return_unbound_request_source_metadata(env,fault):
    values,body=ready(env);data,_,_,_,_,target,_,url=values
    with data[0].tx() as c:
        c.execute(update(journal).values(**({'instance_id':'iinstance_'+'0'*32} if fault=='instance' else {'source_app_id':target})))
    before=snapshot(data[0]);response=data[2].get('/api/projects/'+data[4]+'/registered-text-requests');assert snapshot(data[0])==before
    p=OUT/(os.environ.get('COLD_PROBE_PREFIX','candidate1-independent-')+'discovery-'+fault+'.json');assert not p.exists();p.write_text(json.dumps({'classification':'ACTUAL_SQLITE_API_CONTROLLED_IMMUTABLE_SCOPE_METADATA_CORRUPTION','fault':fault,'status':response.status_code,'text':response.text,'db_unchanged':True,'expected':'Reject metadata whose source_app or instance is not bound to actual owned source Run, without reading protected body.'},indent=2)+'\n')
    assert response.status_code in {403,409},'Project discovery exposed unbound source metadata as valid recovery entry'

def test_committed_owner_close_after_revocation_never_reads_body_or_false_cancels(env):
    from sim2act.db import grants
    values,body=ready(env);data,_,_,_,run,target,resource,url=values
    made=data[2].post(url+'/extract',json=body);assert made.status_code==201
    closing=close_body(data[2],url)
    runtime=data[2].get('/api/apps/'+target).json()['runtime_id']
    with data[0].tx() as c:g=dict(c.execute(select(grants).where(grants.c.principal_id==runtime)).mappings().one())
    revoked=data[2].post('/api/grants/'+g['id']+'/revoke',json={'command':'revoke','version':g['revision']});assert revoked.status_code==200
    before=snapshot(data[0]);barrier=PrivateReadBarrier(data[0],{run['id']},{data[5],resource});barrier.rules['registered_extraction_requests']=(journal,'request_key',{body['request_key']},{'request'})
    with barrier:
        reply=data[2].post(url+'/extraction-request-close',json=closing)
    assert not barrier.evaluated and not barrier.blocked
    assert reply.status_code==200 and reply.json()['state']=='COMMITTED' and reply.json()['app_id']==made.json()['id']
    assert snapshot(data[0])==before
    p=OUT/(os.environ.get('COLD_PROBE_PREFIX','candidate1-independent-')+'committed-revoked-close.json');assert not p.exists();p.write_text(json.dumps({'status':reply.status_code,'body':reply.json(),'db_unchanged':True,'blocked':barrier.blocked,'evaluated':barrier.evaluated,'sql':barrier.statements,'classification':'ACTUAL_SQLITE_API_GRANT_REVOCATION_PROTECTED_CELL_BARRIER'},indent=2)+'\n')

def test_close_a_then_close_b_cannot_make_original_empty_latest_cas_valid(env):
    values,body=ready(env);data,*_,url=values
    a=data[2].post(url+'/extraction-request-close',json=close_body(data[2],url));assert a.status_code==200
    b={**body,'request_key':'independent-key-B'};p=data[2].post(url+'/extraction-requests',json=prepare_body(b,a.json()));assert p.status_code==201
    cb=data[2].post(url+'/extraction-request-close',json=close_body(data[2],url));assert cb.status_code==200
    before=snapshot(data[0]);late={**body,'request_key':'delayed-from-empty-epoch'};r=data[2].post(url+'/extraction-requests',json=prepare_body(late));assert r.status_code==409 and snapshot(data[0])==before
    p=OUT/(os.environ.get('COLD_PROBE_PREFIX','candidate1-independent-')+'closed-highwater-aba.json');assert not p.exists();p.write_text(json.dumps({'status':r.status_code,'body':r.json(),'db_unchanged':True,'latest_key':cb.json()['request_key'],'sequence':cb.json()['sequence'],'classification':'ACTUAL_SQLITE_API_TWO_EXPLICIT_CLOSED_IDENTITIES_AND_STALE_EMPTY_CAS'},indent=2)+'\n')
