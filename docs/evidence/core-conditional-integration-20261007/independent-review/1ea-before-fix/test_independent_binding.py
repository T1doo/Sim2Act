"""Independent HTTP assertions; responses written from public policy, never gold/checker output."""
import copy
import json
import socket
from pathlib import Path

import pytest
from sqlalchemy import select, update

import conftest
import test_conditional_run_bindings as plumbing
from sim2act.db import attempts, events, fingerprint, grants, protocol_jobs, runs


@pytest.fixture
def env(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('Independent review permits MockTransport only')

    monkeypatch.setattr(socket, 'create_connection', no_network)
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    fixture = conftest.env.__wrapped__(tmp_path)
    baseline = next(fixture)
    try:
        yield plumbing.env.__wrapped__(baseline)
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def handwritten(amount=680):
    lines=plumbing.POLICY.read_text().splitlines()
    return {
        'findings': [
            {'rule_id':'R1','applies':'TRUE','citation':{'line':3,'quote':lines[2]}},
            {'rule_id':'R2','applies':'TRUE' if amount>500 else 'FALSE','citation':{'line':4,'quote':lines[3]}},
            {'rule_id':'R3','applies':'FALSE','citation':{'line':5,'quote':lines[4]}},
        ],
        'decision':'BLOCK' if amount>500 else 'ALLOW',
        'next_actions':['obtain_prior_approval'] if amount>500 else ['submit_claim_and_receipt'],
        'deadline_days':10,'absolute_date':'UNKNOWN','receipt_restarts_deadline':False,
        'explanation':'Independent hand-written hypothetical report; not a real reimbursement or semantic signoff.',
    }


def actual_source(env,tmp_path,key='independent-source',scenario=None,output=None):
    public=env[2].get(plumbing.base(env)+'/contract').json()
    body={'resource_id':env[6], 'expected_source_hash':public['source_hash'],
          'expected_contract_fingerprint':public['check_contract_fingerprint'],
          'goal':public['goal'], 'scenario':{'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,
              'amount':680,'receipt_present':True,'approved':False,'elapsed_days':2},
          'request_key':key}
    if scenario is not None: body['scenario']=scenario
    queued=env[2].post(plumbing.base(env)+'/source',json=body)
    assert queued.status_code==202,queued.text
    rid=queued.json()['run_id'];wires=[]
    plumbing.work(env,tmp_path,[plumbing.envelope(resource=env[6]),plumbing.envelope(output or handwritten())],wires)
    result=plumbing.get(env,rid)
    assert result['status']=='WAITING_APPROVAL' and result['semantic_status']=='UNKNOWN'
    assert result['overall_run_acceptance']=='NOT_ACCEPTED'
    request={'expected_result_fingerprint':result['result_fingerprint'],
             'expected_version':result['version'],'expected_fence':result['fence'],'request_key':'independent-check'}
    checked=env[2].post(plumbing.base(env)+'/'+rid+'/checks',json=request)
    assert checked.status_code==201,checked.text
    proof=checked.json()
    assert proof['value']['checks']['check_status']=='PASS'
    if scenario is None:
        assert proof['value']['checks']['decision']=='BLOCK' and proof['value']['candidate_eligible'] is True
    assert proof['value']['semantic_status']=='UNKNOWN' and proof['value']['overall_run_acceptance']=='NOT_ACCEPTED'
    return rid,result,proof,wires,request


@pytest.mark.parametrize('attack',[
    'single_anchor_fence_bool','single_record_fence_bool','both_fence_bool_rehashed',
    'both_version_bool_rehashed','both_expected_fence_bool_rehashed','both_request_extra_rehashed',
    'both_false_eligibility_rehashed','both_wrong_run_rehashed','wrapper_check_id_bool',
    'completion_extra_field','attempt_parameter_extra','current_version','current_fence',
    'source_format','runtime_revoked','old_gate_status_only',
])
def test_independent_http_coherent_attack_denied(env,tmp_path,attack):
    rid,result,record,wires,request=actual_source(env,tmp_path)
    body=plumbing.extract_body(rid,result,record,request_key='independent-extract')
    with env[0].tx() as c:
        changed=copy.deepcopy(record)
        if attack.startswith('both_') or attack.startswith('single_'):
            if attack=='both_version_bool_rehashed':changed['value']['version']=True
            elif attack=='both_expected_fence_bool_rehashed':changed['value']['request']['expected_fence']=True
            elif attack=='both_request_extra_rehashed':changed['value']['request']['caller_pass']=True
            elif attack=='both_false_eligibility_rehashed':changed['value']['candidate_eligible']=False
            elif attack=='both_wrong_run_rehashed':changed['value']['run_id']='run_'+'a'*32
            else:changed['value']['fence']=True
            if attack.startswith('both_'):
                changed['fingerprint']=fingerprint(changed['value'])
                body['expected_check_fingerprint']=changed['fingerprint']
            if attack!='single_anchor_fence_bool':
                c.execute(update(events).where(events.c.run_id==rid,events.c.kind==plumbing.CHECK_EVENT).values(data=changed))
            if attack!='single_record_fence_bool':
                c.execute(update(events).where(events.c.run_id==record['check_id'],events.c.kind==plumbing.ANCHOR_EVENT).values(data=changed))
        elif attack=='wrapper_check_id_bool':
            changed['check_id']=True
            c.execute(update(events).where(events.c.run_id==rid,events.c.kind==plumbing.CHECK_EVENT).values(data=changed))
        elif attack=='completion_extra_field':
            row=c.execute(select(events).where(events.c.run_id==rid,events.c.kind=='PROTOCOL_COMPLETED')).mappings().one()
            c.execute(update(events).where(events.c.id==row['id']).values(data={**row['data'],'caller_pass':True}))
        elif attack=='attempt_parameter_extra':
            row=c.execute(select(attempts).where(attempts.c.run_id==rid).order_by(attempts.c.created_at)).mappings().all()[-1]
            c.execute(update(attempts).where(attempts.c.id==row['id']).values(parameters={**row['parameters'],'private':True}))
        elif attack=='source_format':
            from sim2act.db import resources
            c.execute(update(resources).where(resources.c.id==env[6]).values(format='csv'))
        elif attack=='runtime_revoked':
            current=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
            c.execute(update(grants).where(grants.c.resource_id==env[6],grants.c.principal_id==current['runtime_id']).values(revoked=True))
        elif attack=='old_gate_status_only':
            c.execute(update(runs).where(runs.c.id==rid).values(status='SUCCEEDED'))
        else:
            field='version' if attack=='current_version' else 'fence'
            c.execute(update(runs).where(runs.c.id==rid).values({field:result[field]+1}))
    response=env[2].post(plumbing.base(env)+'/extract',json=body)
    assert response.status_code in (400,403,409),(attack,response.status_code,response.text)
    assert len(wires)==2
    assert not (response.status_code==202)


def test_independent_true_other_run_dual_event_replay(env,tmp_path):
    first,_,old,wires,_=actual_source(env,tmp_path,'independent-first')
    second,result,checked,second_wires,_=actual_source(env,tmp_path,'independent-second')
    with env[0].tx() as c:
        c.execute(update(events).where(events.c.run_id==second,events.c.kind==plumbing.CHECK_EVENT).values(data=old))
    body=plumbing.extract_body(second,result,old,request_key='replayed-other-check')
    response=env[2].post(plumbing.base(env)+'/extract',json=body)
    assert response.status_code in (400,409),response.text
    assert len(wires)==len(second_wires)==2
    assert plumbing.get(env,first)['status']=='WAITING_APPROVAL'


def test_independent_check_is_idempotent_and_original_success_gate_unchanged(env,tmp_path):
    rid,result,record,wires,request=actual_source(env,tmp_path)
    repeat=env[2].post(plumbing.base(env)+'/'+rid+'/checks',json=request)
    assert repeat.status_code==201 and repeat.json()==record
    current=plumbing.get(env,rid)
    assert current['status']=='WAITING_APPROVAL' and current['semantic_status']=='UNKNOWN'
    for key in ['expected_fence','expected_version']:
        altered={**request,key:True}
        assert env[2].post(plumbing.base(env)+'/'+rid+'/checks',json=altered).status_code==422
    old=env[2].post(f'/api/projects/{env[5]}/protocol/extract',json={
        'source_run_id':rid,'expected_source_fingerprint':result['result_fingerprint'],'request_key':'independent-old-extract'})
    assert old.status_code==400,old.text
    assert len(wires)==2


def test_unknown_facts_cannot_be_promoted_by_coherent_dual_receipt(env,tmp_path):
    facts={'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':680,
        'receipt_present':True,'approved':None,'elapsed_days':2}
    output=handwritten();output['decision']='UNKNOWN';output['next_actions']=['clarify_facts']
    rid,result,record,wires,_=actual_source(env,tmp_path,scenario=facts,output=output)
    assert record['value']['candidate_eligible'] is False
    forged=copy.deepcopy(record);forged['value']['candidate_eligible']=True
    forged['fingerprint']=fingerprint(forged['value'])
    with env[0].tx() as c:
        c.execute(update(events).where(events.c.run_id==rid,events.c.kind==plumbing.CHECK_EVENT).values(data=forged))
        c.execute(update(events).where(events.c.run_id==record['check_id'],events.c.kind==plumbing.ANCHOR_EVENT).values(data=forged))
    response=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,result,forged))
    assert response.status_code in (400,409),response.text
    assert len(wires)==2
    Path('/tmp/core-conditional-integration-review/unknown-promotion-result.json').write_text(json.dumps({
        'finite_check_status':record['value']['checks']['check_status'],
        'original_candidate_eligible':False,'coherent_both_events_changed':True,
        'extraction_http':response.status_code,'error_code':response.json()['error']['code'],
        'actual_mock_calls':len(wires),'run_overall_acceptance':'NOT_ACCEPTED','semantic_status':'UNKNOWN',
    },indent=2)+'\n')


def test_independent_public_dag_new_facts_new_receipts_not_run_acceptance(env,tmp_path):
    from sim2act.db import principals
    with env[0].tx() as c:
        authority=fingerprint([dict(r) for r in c.execute(select(grants)).mappings()])
        identities=fingerprint([dict(r) for r in c.execute(select(principals)).mappings()])
    rid,result,record,wires,_=actual_source(env,tmp_path)
    accepted=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,result,record))
    assert accepted.status_code==202,accepted.text
    eid=accepted.json()['run_id'];public=env[2].get(plumbing.base(env)+'/contract').json()
    schema=public['report_schema']
    candidate={'schema_version':'model-protocol.v1',
        'input_schema':{'type':'object','properties':{
            'scenario_json':{'type':'string','maxLength':3000},
            'report_schema_json':{'type':'string','maxLength':5000}},
            'required':['scenario_json','report_schema_json'],'additionalProperties':False},
        'resources':{'rules':env[6]},'steps':[
            {'id':'read_rules','kind':'registered_tool','depends_on':[],
                'inputs':{'resource_id':{'source':'data','ref':'rules','field':'resource_id'}},'tool_ref':'resource.read'},
            {'id':'check_report','kind':'language','depends_on':['read_rules'],
                'inputs':{'content':{'source':'step','ref':'read_rules','field':'content'},
                    'scenario_json':{'source':'input','ref':'input','field':'scenario_json'},
                    'report_schema_json':{'source':'input','ref':'input','field':'report_schema_json'}},
                'instruction':public['goal'],'output_schema':schema}],
        'output_schema':schema,'outputs':{field:{'source':'step','ref':'check_report','field':field} for field in schema['properties']}}
    plumbing.work(env,tmp_path,[plumbing.envelope(candidate)],wires)
    extraction=plumbing.get(env,eid)
    assert extraction['status']=='SUCCEEDED' and extraction['overall_run_acceptance']=='NOT_ACCEPTED'
    plan=extraction['result']['compiled_plan']
    fresh={'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':500,
        'receipt_present':True,'approved':False,'elapsed_days':5}
    accepted=env[2].post(plumbing.base(env)+'/cold',json={
        'extraction_run_id':eid,'expected_plan_fingerprint':plan['plan_fingerprint'],
        'resource_id':env[7],'scenario':fresh,'request_key':'independent-cold'})
    assert accepted.status_code==202,accepted.text
    cid=accepted.json()['run_id']
    plumbing.work(env,tmp_path,[plumbing.envelope(handwritten(500))],wires)
    cold=plumbing.get(env,cid)
    assert cold['status']=='WAITING_APPROVAL' and cold['semantic_status']=='UNKNOWN'
    assert cold['result_fingerprint']!=result['result_fingerprint']
    evidence=cold['result']['protocol_result']['evidence']
    assert evidence['tool_trace'][0]['args']['resource_id']==env[7]
    assert evidence['output']['decision']=='ALLOW'
    checked=env[2].post(plumbing.base(env)+'/'+cid+'/checks',json={
        'expected_result_fingerprint':cold['result_fingerprint'],
        'expected_version':cold['version'],'expected_fence':cold['fence'],'request_key':'independent-cold-check'})
    assert checked.status_code==201,checked.text
    value=checked.json()['value']
    assert value['checks']['check_status']=='PASS' and value['checks']['decision']=='ALLOW'
    assert value['semantic_status']=='UNKNOWN' and value['owner_acceptance']=='PENDING'
    assert value['formal_publication_enabled'] is False and value['overall_run_acceptance']=='NOT_ACCEPTED'
    assert plumbing.get(env,rid)['status']=='WAITING_APPROVAL'
    with env[0].tx() as c:
        assert fingerprint([dict(r) for r in c.execute(select(grants)).mappings()])==authority
        assert fingerprint([dict(r) for r in c.execute(select(principals)).mappings()])==identities
        from sim2act.db import operations, protocol_request_slots
        actual_attempts=[dict(r) for r in c.execute(select(attempts).where(attempts.c.run_id.in_([rid,eid,cid]))).mappings()]
        actual_operations=[dict(r) for r in c.execute(select(operations).where(operations.c.run_id.in_([rid,eid,cid]))).mappings()]
        actual_slots=[dict(r) for r in c.execute(select(protocol_request_slots).where(protocol_request_slots.c.run_id.in_([rid,eid,cid]))).mappings()]
    assert len(actual_attempts)==4 and all(a['status']=='RECEIVED' and a['usage']['status']=='known' for a in actual_attempts)
    assert len(actual_operations)==2 and all(o['status']=='VERIFIED' for o in actual_operations)
    assert len(actual_slots)==4
    assert len(wires)==4
    Path('/tmp/core-conditional-integration-review/positive-chain-result.json').write_text(json.dumps({
        'source':{'status':result['status'],'decision':'BLOCK','finite_check':'PASS','model_attempts':2,'verified_read_operations':1},
        'extraction':{'status':extraction['status'],'candidate_only':True,'model_attempts':1,'candidate_authored':'literal public fixed DAG; no source answers'},
        'cold':{'status':cold['status'],'decision':'ALLOW','finite_check':'PASS','model_attempts':1,'verified_read_operations':1,'new_resource_binding':True,'new_scenario':True,'new_result_fingerprint':True},
        'total_actual_attempts':len(actual_attempts),'all_attempts_received':True,'known_usage_tokens':sum(a['usage']['tokens']['total_tokens'] for a in actual_attempts),
        'total_verified_operations':len(actual_operations),'actual_persistent_request_slots':len(actual_slots),
        'grant_and_principal_rows_unchanged':True,'handwritten_reports':2,'gold_reads':0,
        'live_requests':0,'overall_run_acceptance':'NOT_ACCEPTED','semantic_status':'UNKNOWN','owner_acceptance':'PENDING','formal_publication_enabled':False,
    },indent=2)+'\n')


def literal_candidate(public,rid):
    schema=public['report_schema']
    return {'schema_version':'model-protocol.v1',
        'input_schema':{'type':'object','properties':{
            'scenario_json':{'type':'string','maxLength':3000},
            'report_schema_json':{'type':'string','maxLength':5000}},
            'required':['scenario_json','report_schema_json'],'additionalProperties':False},
        'resources':{'rules':rid},'steps':[
            {'id':'read_rules','kind':'registered_tool','depends_on':[],
                'inputs':{'resource_id':{'source':'data','ref':'rules','field':'resource_id'}},'tool_ref':'resource.read'},
            {'id':'check_report','kind':'language','depends_on':['read_rules'],
                'inputs':{'content':{'source':'step','ref':'read_rules','field':'content'},
                    'scenario_json':{'source':'input','ref':'input','field':'scenario_json'},
                    'report_schema_json':{'source':'input','ref':'input','field':'report_schema_json'}},
                'instruction':public['goal'],'output_schema':schema}],
        'output_schema':schema,'outputs':{field:{'source':'step','ref':'check_report','field':field} for field in schema['properties']}}


def actual_extraction(env,tmp_path):
    rid,result,record,wires,_=actual_source(env,tmp_path)
    accepted=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,result,record))
    assert accepted.status_code==202,accepted.text
    eid=accepted.json()['run_id'];public=env[2].get(plumbing.base(env)+'/contract').json()
    plumbing.work(env,tmp_path,[plumbing.envelope(literal_candidate(public,env[6]))],wires)
    extracted=plumbing.get(env,eid)
    return rid,eid,extracted['result']['compiled_plan'],wires


def actual_cold(env,tmp_path,eid,plan,wires,facts,output,key):
    made=env[2].post(plumbing.base(env)+'/cold',json={
        'extraction_run_id':eid,'expected_plan_fingerprint':plan['plan_fingerprint'],
        'resource_id':env[7],'scenario':facts,'request_key':key})
    assert made.status_code==202,made.text
    rid=made.json()['run_id']
    plumbing.work(env,tmp_path,[plumbing.envelope(output)],wires)
    result=plumbing.get(env,rid)
    assert result['status']=='WAITING_APPROVAL' and result['semantic_status']=='UNKNOWN'
    response=env[2].post(plumbing.base(env)+'/'+rid+'/checks',json={
        'expected_result_fingerprint':result['result_fingerprint'],'expected_version':result['version'],
        'expected_fence':result['fence'],'request_key':key+'-check'})
    assert response.status_code==201,response.text
    value=response.json()['value']
    assert value['checks']['check_status']=='PASS'
    assert value['semantic_status']=='UNKNOWN' and value['overall_run_acceptance']=='NOT_ACCEPTED'
    with env[0].tx() as c:
        from sim2act.db import operations
        actual=c.execute(select(attempts).where(attempts.c.run_id==rid)).mappings().one()
        operation=c.execute(select(operations).where(operations.c.run_id==rid)).mappings().one()
    assert actual['status']=='RECEIVED' and actual['usage']['status']=='known'
    assert operation['status']=='VERIFIED' and operation['receipt']['data']['resource_id']==env[7]
    assert result['result']['protocol_result']['evidence']['output']['deadline_days']==10
    assert result['result']['protocol_result']['evidence']['output']['receipt_restarts_deadline'] is False
    return {'case':key,'finite_check':value['checks']['check_status'],'decision':value['checks']['decision'],
        'candidate_eligible':value['candidate_eligible'],'run_status':result['status'],
        'overall_run_acceptance':value['overall_run_acceptance'],'semantic_status':'UNKNOWN',
        'received_attempts':1,'known_tokens':actual['usage']['tokens']['total_tokens'],
        'verified_fresh_read_operations':1,'deadline_days':10,'receipt_restarts_deadline':False,
        'result_fingerprint':result['result_fingerprint']}


def test_independent_actual_cold_501_still_requires_prior_approval(env,tmp_path):
    source,eid,plan,wires=actual_extraction(env,tmp_path)
    facts={'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':501,
        'receipt_present':True,'approved':False,'elapsed_days':2}
    case=actual_cold(env,tmp_path,eid,plan,wires,facts,handwritten(501),'cold-501-unapproved')
    assert case['decision']=='BLOCK' and case['candidate_eligible'] is True
    assert len(wires)==4 and plumbing.get(env,source)['status']=='WAITING_APPROVAL'
    Path('/tmp/core-conditional-integration-review/cold-501-result.json').write_text(json.dumps(case,indent=2)+'\n')


def test_independent_actual_cold_missing_then_restored_receipt_keeps_original_deadline(env,tmp_path):
    source,eid,plan,wires=actual_extraction(env,tmp_path)
    facts={'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':500,
        'receipt_present':False,'approved':False,'elapsed_days':8}
    output=handwritten(500);output['findings'][2]['applies']='TRUE'
    output['decision']='BLOCK';output['next_actions']=['obtain_receipt']
    missing=actual_cold(env,tmp_path,eid,plan,wires,facts,output,'cold-missing-receipt-day8')
    assert missing['decision']=='BLOCK' and missing['candidate_eligible'] is True
    facts={**facts,'receipt_present':True,'elapsed_days':11}
    output=handwritten(500);output['decision']='UNKNOWN';output['next_actions']=['clarify_late_policy']
    restored=actual_cold(env,tmp_path,eid,plan,wires,facts,output,'cold-restored-receipt-day11')
    assert restored['decision']=='UNKNOWN' and restored['candidate_eligible'] is False
    assert missing['result_fingerprint']!=restored['result_fingerprint']
    assert len(wires)==5 and plumbing.get(env,source)['status']=='WAITING_APPROVAL'
    Path('/tmp/core-conditional-integration-review/cold-receipt-deadline-result.json').write_text(json.dumps({
        'missing':missing,'restored':restored,'actual_total_calls':5,
        'only_distinct_hypotheses_not_verified_real_case_history':True},indent=2)+'\n')


def test_independent_unknown_trip_cannot_gain_eligibility_from_dual_event_rehash(env,tmp_path):
    facts={'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':None,'amount':500,
        'receipt_present':True,'approved':False,'elapsed_days':None}
    output=handwritten(500);output['findings'][0]['applies']='UNKNOWN'
    output['decision']='UNKNOWN';output['next_actions']=['clarify_facts']
    rid,result,record,wires,_=actual_source(env,tmp_path,scenario=facts,output=output)
    assert record['value']['checks']['check_status']=='PASS' and record['value']['candidate_eligible'] is False
    changed=copy.deepcopy(record);changed['value']['candidate_eligible']=True
    changed['fingerprint']=fingerprint(changed['value'])
    with env[0].tx() as c:
        c.execute(update(events).where(events.c.run_id==rid,events.c.kind==plumbing.CHECK_EVENT).values(data=changed))
        c.execute(update(events).where(events.c.run_id==record['check_id'],events.c.kind==plumbing.ANCHOR_EVENT).values(data=changed))
    response=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,result,changed))
    assert response.status_code==409 and response.json()['error']['code']=='VERSION_CONFLICT'
    assert len(wires)==2 and plumbing.get(env,rid)['status']=='WAITING_APPROVAL'
    Path('/tmp/core-conditional-integration-review/unknown-trip-result.json').write_text(json.dumps({
        'finite_check':'PASS','decision':'UNKNOWN','original_candidate_eligible':False,
        'both_events_eligible_rehashed':True,'extraction_http':409,'actual_mock_calls':2,
        'semantic_status':'UNKNOWN','overall_run_acceptance':'NOT_ACCEPTED'},indent=2)+'\n')
