import copy
import json
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update, delete
from conftest import env as original_env
from test_conditional_run_bindings import env as bounded_env
from test_report_presentations import prepared
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits, setup_draft
from sim2act.api import create_app
from sim2act.db import Store, fingerprint, grants, resources, app_drafts
from sim2act.db import delivery_graph_requests as ledger
from sim2act import project_revalidation as subject

ROOT=Path('/tmp/sim2act-project-revalidation-independent-20261009')

@pytest.fixture
def env(tmp_path):
    generator=original_env.__wrapped__(tmp_path)
    try:
        yield bounded_env.__wrapped__(next(generator))
    finally:
        generator.close()

def arrange(env,tmp_path):
    app,anchor,url,_,_,wires=prepared(env,tmp_path,peer=True)
    base=url.removesuffix('report-presentations')+'scope-checks'
    response=env[2].get(base+'/options',params={'plan_key':'presentation-plan'})
    assert response.status_code==200,response.text
    choices=response.json()
    selections=[]
    for entry in choices['applications']:
        if not entry['supported']: continue
        selection={'kind':entry['kind'],'app_id':entry['app_id'],'expected_graph_fingerprint':entry['binding']['graph_fingerprint']}
        if selection['kind']=='CSV':
            assert entry['columns']==['amount'] # original independent source; no author quantity fixture
            selection['input']={'column':'amount'}
        else:
            r=entry['runs'][0]
            selection.update(run_id=r['run_id'],expected_run_version=r['version'],expected_run_fence=r['fence'],expected_result_fingerprint=r['result_fingerprint'])
        selections.append(selection)
    body=dict(plan_key='presentation-plan',expected_plan_fingerprint=choices['plan_fingerprint'],expected_options_fingerprint=choices['options_fingerprint'],selections=selections,consent='CONFIRM_EXACT_PROJECT_DETERMINISTIC_CHECKS',request_key='review-proof')
    return app,anchor,base,choices,body,wires

def assert_no_write(env,before,response,allowed=(400,403,409,422)):
    assert response.status_code in allowed,response.text
    assert snapshot(env)==before

def test_independent_original_amount_report_cold_and_only_two_receipt_rows(env,tmp_path):
    app,anchor,base,choices,body,wires=arrange(env,tmp_path)
    before=snapshot(env)
    response=env[2].post(base,json=body)
    assert response.status_code==201,response.text
    accepted=response.json()
    csv=next(x for x in accepted['applications'] if x['selection']['kind']=='CSV')
    rep=next(x for x in accepted['applications'] if x['selection']['kind']=='REPORT')
    assert Decimal(csv['actual']['output']['sum'])==Decimal('4') and csv['actual']['output']['count']==2
    assert csv['actual']['input']=={'column':'amount'}
    assert len(csv['actual']['actual_reads'])==2
    assert {x['id']:x['status'] for x in csv['actual']['checks']}=={'source.readback':'PASS','count.independent':'PASS','sum.independent':'PASS'}
    assert rep['actual']['status']=='PASS' and rep['actual']['explanation_status']=='NOT_CHECKED'
    proof=rep['actual']['archived_run']
    assert proof['checks']['check_status']=='PASS' and proof['semantic_status']=='UNKNOWN'
    assert accepted['executed_checks_status']=='PASS' and accepted['deterministic_status']=='PARTIAL'
    assert accepted['omitted_checks'][0]['declaration_status']=='NONCANONICAL_NAMED_SOURCE'
    assert accepted['project_revalidation_status']=='BLOCKED_PARTIAL' and not accepted['project_revalidation_completed']
    assert accepted['overall_run_acceptance']=='NOT_ACCEPTED' and accepted['model_requests']==accepted['business_writes']==0
    assert next(v for v in accepted['global_invariants'] if v['id']=='dependency_completeness')['status']=='BLOCKED_UNKNOWN'
    for entry in accepted['applications']:
        source=next(x for x in choices['applications'] if x['app_id']==entry['app_id'])
        assert {x['node_id'] for x in entry['declared_checks']}=={x['id'] for x in source['checks']}
    after=snapshot(env)
    for table in before:
        if table!=ledger.name: assert after[table]==before[table],table
    inserted=[r for r in after[ledger.name] if r not in before[ledger.name]]
    assert len(inserted)==2 and {r['kind'] for r in inserted}=={subject.KIND,subject.KIND+'_seal'}
    fresh=Store(env[1].database_url,test_only=True)
    cold=TestClient(create_app(fresh,env[1]));cold.headers['Authorization']='Bearer synthetic-test-A'
    try:
        for answer in [cold.get(base+'/'+body['request_key']),cold.post(base,json=body),cold.get(base,params={'plan_key':body['plan_key']})]:
            assert answer.status_code in (200,201),answer.text
        assert cold.get(base+'/'+body['request_key']).json()['check_fingerprint']==accepted['check_fingerprint']
        assert snapshot(env)==after and len(wires)==4
    finally: cold.close();fresh.engine.dispose()
    plan=env[2].get(base.removesuffix('scope-checks')+'plans').json()['items'][0]
    (ROOT/'fixture.json').write_text(json.dumps(dict(app=app,anchor=anchor,plan=plan,options=choices,receipt=accepted,body=body)))

@pytest.mark.parametrize('attack',['remove-report','swap-kind','duplicate','grant-claim','nested-extra','bool-fence','foreign-run','bad-options','bad-plan','surrogate-column','key-too-long','stale-run-version','stale-run-fence','wrong-result-proof'])
def test_strict_confirmation_independently_rejects_without_write(env,tmp_path,attack):
    _,_,base,_,body,_=arrange(env,tmp_path)
    csv=next(s for s in body['selections'] if s['kind']=='CSV');rep=next(s for s in body['selections'] if s['kind']=='REPORT')
    if attack=='remove-report': body['selections'].remove(rep)
    elif attack=='swap-kind': csv['kind']='REPORT'
    elif attack=='duplicate': body['selections'].append(copy.deepcopy(rep))
    elif attack=='grant-claim': body['authorized']=True
    elif attack=='nested-extra': csv['input']['gold_sum']='4'
    elif attack=='bool-fence': rep['expected_run_fence']=False
    elif attack=='foreign-run': rep['run_id']='run_'+'0'*32
    elif attack=='bad-options': body['expected_options_fingerprint']='a'*64
    elif attack=='bad-plan': body['plan_key']='not-accepted'
    elif attack=='surrogate-column': csv['input']['column']='\udfff'
    elif attack=='key-too-long': body['request_key']='a'*101
    elif attack=='stale-run-version': rep['expected_run_version']+=1
    elif attack=='stale-run-fence': rep['expected_run_fence']+=1
    elif attack=='wrong-result-proof': rep['expected_result_fingerprint']='b'*64
    response=env[2].post(base,content=json.dumps(body),headers={'Content-Type':'application/json'}) if attack=='surrogate-column' else env[2].post(base,json=body)
    assert_no_write(env,snapshot(env),response)

@pytest.mark.parametrize('damage',['revoked-source','changed-byte','removed-seal','both-rehashed-receipts','plan-seal','same-key-body','foreign-owner'])
def test_persisted_proof_rechecks_current_authority_source_and_independent_seals(env,tmp_path,damage):
    _,_,base,_,body,_=arrange(env,tmp_path)
    assert env[2].post(base,json=body).status_code==201
    with env[0].tx() as c:
        if damage=='revoked-source': c.execute(update(grants).where(grants.c.project_id==env[5],grants.c.tool_ref=='resource.read').values(revoked=True))
        elif damage=='changed-byte': c.execute(update(resources).where(resources.c.id==env[6]).values(content='item,amount\na,3\nb,1\n')) # deliberately same sum, broken byte/hash
        elif damage=='removed-seal': c.execute(delete(ledger).where(ledger.c.kind==subject.KIND+'_seal'))
        elif damage in ('both-rehashed-receipts','plan-seal'):
            kinds=[subject.KIND,subject.KIND+'_seal'] if damage=='both-rehashed-receipts' else ['plan_seal']
            for row in c.execute(select(ledger).where(ledger.c.kind.in_(kinds))).mappings():
                value=copy.deepcopy(row['snapshot'])
                if damage=='both-rehashed-receipts':
                    value['response']['applications'][0]['actual']['status']='FAIL'
                    raw={k:v for k,v in value['response'].items() if k!='check_fingerprint'}
                    value['response']['check_fingerprint']=fingerprint(raw)
                else: value['response']['scope_expansion']['omissions']=[]
                c.execute(update(ledger).where(ledger.c.app_id==row['app_id'],ledger.c.kind==row['kind'],ledger.c.request_key==row['request_key']).values(snapshot=value,fingerprint=fingerprint(value)))
    if damage=='foreign-owner': env[2].headers['Authorization']='Bearer synthetic-test-B'
    if damage=='same-key-body': body['selections'].reverse()
    before=snapshot(env)
    response=env[2].post(base,json=body) if damage=='same-key-body' else env[2].get(base+'/'+body['request_key'])
    assert_no_write(env,before,response)

def test_wrong_registered_count_has_independent_failed_receipt_and_cold_recompute(env,tmp_path,monkeypatch):
    _,_,base,_,body,_=arrange(env,tmp_path)
    actual=subject.authorized_read
    def corrupt(*args,**kwargs):
        output=actual(*args,**kwargs)
        return {**output,'count':999} if args[5]=='data.aggregate_csv' else output
    monkeypatch.setattr(subject,'authorized_read',corrupt)
    response=env[2].post(base,json=body)
    assert response.status_code==201,response.text
    receipt=response.json();assert receipt['deterministic_status']==receipt['executed_checks_status']=='FAIL'
    csv=next(a['actual'] for a in receipt['applications'] if a['selection']['kind']=='CSV')
    assert next(v for v in csv['checks'] if v['id']=='count.independent')['status']=='FAIL'
    monkeypatch.setattr(subject,'authorized_read',actual)
    assert_no_write(env,snapshot(env),env[2].get(base+'/'+body['request_key']))

def test_member_addition_and_peer_lock_aba_prevent_old_proof(env,tmp_path):
    _,_,base,choices,body,_=arrange(env,tmp_path)
    assert env[2].post(base,json=body).status_code==201
    target=next(s for s in body['selections'] if s['kind']=='CSV')['app_id']
    url=f'/api/projects/{env[5]}/apps/{target}/delivery-graph'
    for revision,locked in enumerate((True,False)):
        anchor=env[2].get(url).json();n=next(x for x in anchor['graph']['nodes'] if x['kind']=='VIEW')
        ack=dict(expected_graph_fingerprint=anchor['graph_fingerprint'],expected_graph_revision=anchor['graph_revision'],change=dict(node_id=n['id'],expected_revision=n['revision'],expected_content_fingerprint=n['content_fingerprint']),expected_lock_revision=revision,locked=locked,request_key=f'review-lock-{revision}',consent='CONFIRM_EXACT_PROJECT_EDIT_LOCK')
        lock=env[2].post(url+'/manual-locks',json=ack);assert lock.status_code==201,lock.text
        entry=next(x for x in choices['applications'] if x['app_id']==target)
        derived=env[2].post(url+'/derive',json={'expected_candidate_fingerprint':entry['binding']['candidate_fingerprint'],'request_key':f'review-derive-{revision}'})
        assert derived.status_code==201,derived.text
    assert_no_write(env,snapshot(env),env[2].get(base+'/'+body['request_key']))

def test_added_authorized_member_invalidates_original_plan_not_silently_omitted(env,tmp_path):
    _,_,base,_,body,_=arrange(env,tmp_path)
    resource=env[2].post(f'/api/projects/{env[5]}/resources',json={'name':'new-member','format':'csv','content':'amount\n5\n'}).json()['id']
    aid,_=setup_draft((*env[:6],resource))
    assert aid
    assert_no_write(env,snapshot(env),env[2].post(base,json=body))

def test_unknown_member_namespace_is_not_unsupported_omission(env,tmp_path):
    _,_,base,_,body,_=arrange(env,tmp_path)
    with env[0].tx() as c:
        wrapper=c.execute(select(app_drafts).where(app_drafts.c.project_id==env[5])).mappings().all()
        row=next(x for x in wrapper if x['candidate'].get('namespace')=='bounded-conditional-app.v1')
        candidate=copy.deepcopy(row['candidate']);candidate['namespace']='unknown-but-rehashed'
        c.execute(update(app_drafts).where(app_drafts.c.id==row['id']).values(candidate=candidate,fingerprint=fingerprint(candidate)))
    assert_no_write(env,snapshot(env),env[2].post(base,json=body))

def test_canonical_missing_graph_enumerates_declared_checks_then_revocation_is_fatal(env,tmp_path):
    with env[0].tx() as c:
        resource=c.execute(select(resources.c.id).where(resources.c.project_id==env[5],resources.c.format=='csv')).scalar_one()
    underived,_=setup_draft((*env[:6],resource))
    _,_,base,choices,body,_=arrange(env,tmp_path)
    omission=next(x for x in choices['omitted_checks'] if x['app_id']==underived)
    assert omission['reason']=='GRAPH_NOT_DERIVED' and omission['declaration_status']=='TRUSTED_GRAPH_NOT_DERIVED'
    assert omission['declared_checks'] and all(x['status']=='NOT_RUN' for x in omission['declared_checks'])
    accepted=env[2].post(base,json=body)
    assert accepted.status_code==201,accepted.text
    assert omission in accepted.json()['omitted_checks'] and accepted.json()['deterministic_status']=='PARTIAL'
    with env[0].tx() as c:
        runtime=c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id==underived)).scalar_one()
        c.execute(update(grants).where(grants.c.principal_id==runtime,grants.c.resource_id==resource).values(revoked=True))
    before=snapshot(env)
    for response in (env[2].get(base+'/options',params={'plan_key':body['plan_key']}),env[2].get(base+'/'+body['request_key']),env[2].post(base,json=body)):
        assert_no_write(env,before,response)

def test_extreme_precision_is_not_run_instead_of_false_pass(env,tmp_path):
    content='item,amount\na,1e-1001\n'
    with env[0].tx() as c:
        c.execute(update(resources).where(resources.c.project_id==env[5],resources.c.format=='csv').values(content=content,hash=hashlib.sha256(content.encode()).hexdigest()))
    _,_,base,_,body,_=arrange(env,tmp_path)
    response=env[2].post(base,json=body);assert response.status_code==201,response.text
    value=response.json();csv=next(x['actual'] for x in value['applications'] if x['selection']['kind']=='CSV')
    assert csv['status']=='NOT_RUN' and csv['reason']=='NUMERIC_PRECISION_OUTSIDE_BOUNDED_ORACLE'
    assert next(x for x in csv['checks'] if x['id']=='sum.independent')['status']=='NOT_RUN'
    assert value['executed_checks_status']=='NOT_RUN' and value['deterministic_status']=='PARTIAL'
    assert value['overall_run_acceptance']=='NOT_ACCEPTED'

@pytest.mark.parametrize('target',['discriminator','extra-value','extra-key','nested-extra-key'])
def test_escaped_unicode_all_json_positions_reject_safely(env,tmp_path,target):
    _,_,base,_,body,_=arrange(env,tmp_path)
    if target=='discriminator': body['selections'][0]['kind']='\ud800'
    elif target=='extra-value': body['unexpected']='\ud800'
    elif target=='extra-key': body['\ud800']='ordinary'
    else: body['selections'][0]['\ud800']={'safe':'safe'}
    before=snapshot(env)
    response=env[2].post(base,content=json.dumps(body),headers={'Content-Type':'application/json'})
    assert_no_write(env,before,response)

@pytest.mark.parametrize('format',['csv','txt'])
def test_same_semantic_source_with_valid_new_hash_is_exact_source_drift_not_omission(env,tmp_path,format):
    _,_,base,_,body,_=arrange(env,tmp_path)
    assert env[2].post(base,json=body).status_code==201
    with env[0].tx() as c:
        row=c.execute(select(resources).where(resources.c.project_id==env[5],resources.c.format==format)).mappings().first()
        content='item,amount\nb,2.75\na,1.25\n' if format=='csv' else row['content']+'\n'
        c.execute(update(resources).where(resources.c.id==row['id']).values(content=content,hash=hashlib.sha256(content.encode()).hexdigest()))
    before=snapshot(env)
    for response in (env[2].get(base+'/options',params={'plan_key':body['plan_key']}),env[2].get(base+'/'+body['request_key']),env[2].post(base,json={**body,'request_key':'drift-new-key'})):
        assert_no_write(env,before,response)

def test_schema_valid_archived_report_with_wrong_decision_fails_real_rule_recheck(env,tmp_path,monkeypatch):
    import test_report_presentations as original_fixture
    build=original_fixture.independent_report
    def wrong(*args,**kwargs):
        result=build(*args,**kwargs)
        result['decision']='BLOCK' # source/facts500 require ALLOW; valid output schema alone is insufficient
        return result
    monkeypatch.setattr(original_fixture,'independent_report',wrong)
    _,_,base,_,body,wires=arrange(env,tmp_path)
    response=env[2].post(base,json=body);assert response.status_code==201,response.text
    value=response.json();report=next(x['actual'] for x in value['applications'] if x['selection']['kind']=='REPORT')
    assert report['status']=='FAIL' and report['archived_run']['checks']['check_status']=='FAIL'
    assert value['executed_checks_status']==value['deterministic_status']=='FAIL'
    assert report['explanation_status']=='NOT_CHECKED' and value['overall_run_acceptance']=='NOT_ACCEPTED'
    assert len(wires)==4
