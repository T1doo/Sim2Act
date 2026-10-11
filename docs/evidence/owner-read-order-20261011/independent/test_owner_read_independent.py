"""Independent actual SQLite, Worker and HTTP probes; simulated owner declarations."""
import copy,json
from pathlib import Path
import pytest
from sqlalchemy import event
import test_owner_acceptance as owner
import test_goal_text_ui as ui

OUT=Path('/tmp/owner-read-order-review-20261011')


def test_actual_same_sequence_states_and_owned_scope(env,monkeypatch):
    data,release,instance,job=owner.flow(env)
    store,_,client,user,pid,text,_=data
    empty=owner.state(data,instance)
    review,_=owner.prepare(data,release,instance,job)
    pending=owner.state(data,instance)
    with monkeypatch.context() as temporal:
        temporal.setattr(owner.time,'time',lambda:review['payload']['expires_at']+1)
        expired=owner.state(data,instance)
    assert pending['owner_acceptance']=='PENDING' and expired['owner_acceptance']=='EXPIRED'
    assert pending['sequence']==expired['sequence']==1 and pending['history']==expired['history']
    body=owner.choice_body(review,key='independent-accepted')
    assert client.post(owner.path(instance)+'-requests',json=body).status_code==201
    accepted=owner.state(data,instance)
    assert accepted['owner_acceptance']=='ACCEPTED' and accepted['sequence']==2
    grant_rows=client.get(f'/api/projects/{pid}/grants').json()
    grant=next(g for g in grant_rows if g['principal_id']==user and g['resource_id']==text and g['tool_ref']=='resource.read' and not g['revoked'])
    revoke=client.post('/api/grants/'+grant['id']+'/revoke',json={'command':'revoke','version':grant['revision']})
    assert revoke.status_code==200 and revoke.json()['status']=='REVOKED'
    queries=[]
    def listen(conn,cursor,statement,parameters,context,executemany):queries.append(statement)
    event.listen(store.engine,'before_cursor_execute',listen)
    try:
        stale=owner.state(data,instance)
        keyed=owner.state(data,instance,'independent-accepted')
    finally:event.remove(store.engine,'before_cursor_execute',listen)
    assert stale['owner_acceptance']=='STALE' and not stale['content_access']
    assert stale['sequence']==accepted['sequence']==2 and stale['history']==accepted['history']
    assert 'payload' not in keyed['recovered'] and keyed['owner_acceptance']=='STALE'
    assert not any('internal_owner_records.payload' in q.lower() for q in queries)
    for state in [empty,pending,expired,accepted,stale,keyed]:
        assert (state['principal_id'],state['project_id'],state['instance_id'],state['app_id'])==(user,pid,instance['id'],instance['source_app_id'])
        assert state['formal_publication_enabled'] is False and state['technical_semantic_status']=='UNKNOWN'
    stop={'command':'REVOKE','request_key':'metadata-stop-after-grant','expected_sequence':2,'target_id':accepted['latest']['id'],'target_fingerprint':accepted['latest']['fingerprint'],'reason':'SIMULATED metadata stop after actual grant HTTP revocation'}
    assert client.post(owner.path(instance)+'-requests',json=stop).status_code==201
    stopped=owner.state(data,instance)
    assert stopped['owner_acceptance']=='REVOKED' and stopped['sequence']==3 and not stopped['content_access']
    (OUT/'actual-owner-state-envelopes.json').write_text(json.dumps({'classification':'ACTUAL_SQLITE_NORMAL_WORKER_IN_PROCESS_HTTP','real_owner_signoff':'NOT_RUN','live_models':0,'empty':empty,'pending':pending,'expired':expired,'accepted':accepted,'stale':stale,'keyed_stale':keyed,'stopped':stopped,'grant_revoke_http_status':revoke.status_code,'metadata_read_sql':queries},ensure_ascii=False,indent=2)+'\n')


def test_actual_http_jsdom_same_sequence_stale(env,tmp_path,monkeypatch):
    original=ui.subprocess.Popen
    driver=OUT/'goal_text_ui_same_sequence.cjs'
    def launch(command,*args,**kwargs):
        if command[:2]==['node','tests/goal_text_ui.cjs']:command=[command[0],str(driver),*command[2:]]
        return original(command,*args,**kwargs)
    monkeypatch.setattr(ui.subprocess,'Popen',launch)
    monkeypatch.setenv('NODE_PATH','/workspace/node-tools/node_modules')
    monkeypatch.setenv('SIM2ACT_PA_EVIDENCE_DIR',str(OUT/'independent-same-sequence-pages'))
    ui.test_goal_text_offline_page_actual_worker(env,tmp_path,'owner-read-order-same-sequence-stale')
