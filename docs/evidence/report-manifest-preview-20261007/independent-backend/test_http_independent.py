"""Independent HTTP oracles; existing source-chain helpers are setup plumbing only."""
import copy
import importlib.util
import json
import sys
from pathlib import Path
import pytest
from sqlalchemy import select,update
REPO=Path('/workspace/Sim2Act-report-manifest-preview')
sys.path.insert(0,str(REPO/'tests'))
from test_conditional_run_bindings import env as bounded_env, envelope,work
from test_conditional_apps import saved
from sim2act.db import app_drafts,app_previews,task_extractions,protocol_jobs,runs,meta,fingerprint
from sim2act.contracts import Limits,schema_check,validate_value
from sim2act.errors import DomainError
spec=importlib.util.spec_from_file_location('independent_seed',REPO/'tests/conftest.py')
seed=importlib.util.module_from_spec(spec);spec.loader.exec_module(seed)
@pytest.fixture
def env(tmp_path):
    gen=seed.env.__wrapped__(tmp_path)
    base=next(gen)
    try:yield bounded_env.__wrapped__(base)
    finally:
        try:next(gen)
        except StopIteration:pass

def promote(env,tmp_path):
    named,_,wires=saved(env,tmp_path)
    r=env[2].post(f'/api/projects/{env[5]}/conditional-apps/{named["id"]}/manifest-preview',json={'expected_app_fingerprint':named['fingerprint'],'request_key':'independent-manifest'})
    assert r.status_code==201,r.text
    return r.json(),named,wires

def snap(env):
    with env[0].tx() as c:
        return {n:fingerprint([dict(r) for r in c.execute(select(t).order_by(*t.primary_key.columns)).mappings()]) for n,t in meta.tables.items()}

def scenario(amount=501,**changes):
    return {'kind':'HYPOTHETICAL_EMPLOYEE','trip_ended':True,'amount':amount,'receipt_present':True,'approved':False,'elapsed_days':10,**changes}

def response_report(decision='BLOCK',unknown=False):
    lines=(REPO/'docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt').read_text().splitlines()
    return {'findings':[{'rule_id':rid,'applies':state,'citation':{'line':line,'quote':lines[line-1]}} for rid,state,line in [('R3','FALSE',5),('R1','TRUE',3),('R2','UNKNOWN' if unknown else 'TRUE',4)]],'decision':decision,'next_actions':['clarify_facts'] if unknown else ['obtain_prior_approval'],'deadline_days':10,'absolute_date':'UNKNOWN','receipt_restarts_deadline':False,'explanation':'Independently hand-written; explanation not accepted as evidence.'}

@pytest.mark.parametrize('damage',['source-null','runtime-bool','budget','history-key'])
def test_http_binding_tamper_denies_without_new_write(env,tmp_path,damage):
    app,_,_=promote(env,tmp_path)
    if damage=='source-null':
        with env[0].tx() as c:c.execute(update(runs).where(runs.c.id==app['candidate']['report_proof']['source_run_id']).values(result=None))
    elif damage in {'runtime-bool','budget'}:
        bad=copy.deepcopy(app['candidate'])
        if damage=='runtime-bool':bad['manifest']['revision']=True
        else:
            for value in [bad['manifest']['runtime_limits'],bad['actions'][0]['limits'],bad['report_proof']['limits']]:value['max_requests']=2
        with env[0].tx() as c:
            row=c.execute(select(task_extractions).where(task_extractions.c.app_id==app['id'])).mappings().one()
            frozen=copy.deepcopy(row['snapshot']);frozen['candidate']=bad;frozen['candidate_fingerprint']=fingerprint(bad)
            c.execute(update(app_drafts).where(app_drafts.c.id==app['id']).values(candidate=bad,fingerprint=fingerprint(bad)))
            c.execute(update(task_extractions).where(task_extractions.c.app_id==app['id']).values(snapshot=frozen))
    else:
        path=f'/api/projects/{env[5]}/apps/{app["id"]}/previews'
        body={'expected_candidate_fingerprint':app['fingerprint'],'input':scenario(),'request_key':'history'}
        accepted=env[2].post(path,json=body);assert accepted.status_code==202
        with env[0].tx() as c:c.execute(update(runs).where(runs.c.id==accepted.json()['run_id']).values(request_key='different-logical-operation'))
    before=snap(env)
    r=env[2].get(f'/api/projects/{env[5]}/apps/{app["id"]}')
    assert r.status_code in {400,403,409},r.text
    assert snap(env)==before

@pytest.mark.parametrize('bad',[{'type':'integer','nullable':1},{'type':'string','nullable':True},{'type':'integer','nullable':True,'enum':[True]}])
def test_nullable_closed_invalid_schema(bad):
    with pytest.raises(DomainError):schema_check(bad)

def test_nullable_enum_does_not_bypass_type_or_enum():
    s={'type':'integer','nullable':True,'enum':[None,500]};schema_check(s)
    validate_value(s,None);validate_value(s,500)
    for value in [True,500.0,'500',501]:
        with pytest.raises(DomainError):validate_value(s,value)
    with pytest.raises(DomainError):validate_value({'type':'integer','nullable':True,'enum':[500]},None)

def test_actual_new_scenarios_independent_reports_and_unknown_stays_unknown(env,tmp_path):
    app,_,wires=promote(env,tmp_path)
    before=snap(env);authority={k:before[k] for k in ['principals','grants']}
    seen=[]
    for key,facts,output in [('independent501',scenario(),response_report()),('independent-unknown',scenario(amount=None,approved=True),response_report('UNKNOWN',True))]:
        body={'expected_candidate_fingerprint':app['fingerprint'],'input':facts,'request_key':key}
        path=f'/api/projects/{env[5]}/apps/{app["id"]}/previews'
        accepted=env[2].post(path,json=body);assert accepted.status_code==202,accepted.text
        rid=accepted.json()['run_id'];seen.append(rid)
        assert env[2].post(path,json=body).json()['run_id']==rid
        work(env,tmp_path,[envelope(output)],wires)
        run=env[2].get(f'/api/projects/{env[5]}/conditional-runs/{rid}');assert run.status_code==200,run.text
        run=run.json();assert run['status']=='WAITING_APPROVAL' and run['overall_run_acceptance']=='NOT_ACCEPTED'
        assert run['result']['protocol_result']['evidence']['output']==output
        check=env[2].post(f'/api/projects/{env[5]}/conditional-runs/{rid}/checks',json={'expected_result_fingerprint':run['result_fingerprint'],'expected_version':run['version'],'expected_fence':run['fence'],'request_key':key+'-check'})
        assert check.status_code in {200,201},check.text
        value=check.json()['value']
        assert value['semantic_status']=='UNKNOWN' and value['overall_run_acceptance']=='NOT_ACCEPTED'
        assert value['checks']['check_status']=='PASS' and value['checks']['decision']==output['decision']
        assert value['candidate_eligible'] is (output['decision']!='UNKNOWN')
        with env[0].tx() as c:
            job=c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id==rid)).mappings().one()
        assert json.loads(job['accepted_snapshot']['payload']['inputs']['scenario_json'])==facts
        assert fingerprint(job['accepted_snapshot']['limits'])==fingerprint(app['candidate']['manifest']['runtime_limits'])
    assert len(set(seen))==2
    current=snap(env);assert {k:current[k] for k in authority}==authority
    history=env[2].get(f'/api/projects/{env[5]}/apps/{app["id"]}/history');assert history.status_code==200
    assert {r['run']['run_id'] for r in history.json()['history']}==set(seen)
    cold_wires=wires[-2:]
    assert len(cold_wires)==2
    for wire in cold_wires:
        text=json.dumps(wire)
        assert 'Independent test response. No business action executed.' not in text
        assert 'Hand-authored mock response; explanation is NOT_CHECKED.' not in text
    evidence={'source':'994e5e9c7e5cef7cb605f0e53494cd2c671437ae','new_run_ids':seen,'cold_wire_fingerprints':[fingerprint(w) for w in cold_wires],'cold_requests':2,'known_usage_per_request':20,'authority_rows_unchanged':True,'decisions':['BLOCK','UNKNOWN'],'finite_check_status':['PASS','PASS'],'candidate_eligible':[True,False],'run_status':'WAITING_APPROVAL','semantic_status':'UNKNOWN','overall_acceptance':'NOT_ACCEPTED','cold_payload_only_new_typed_scenario':True,'source_report_text_not_in_actual_cold_wire':True}
    Path('/tmp/v5-manifest-cold-independent-review/positive-receipts.json').write_text(json.dumps(evidence,indent=2))

@pytest.mark.parametrize('extra',['gold','candidate','report','permissions','runtime_id'])
def test_closed_preview_extra_no_writes(env,tmp_path,extra):
    app,_,_=promote(env,tmp_path);before=snap(env)
    r=env[2].post(f'/api/projects/{env[5]}/apps/{app["id"]}/previews',json={'expected_candidate_fingerprint':app['fingerprint'],'input':scenario(),'request_key':'invalid',extra:{'secret':'test-only'}})
    assert r.status_code==422,r.text
    assert snap(env)==before

def test_tightened_platform_cannot_persist_unreadable_manifest(env,tmp_path):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from sim2act.api import create_app
    named,_,_=saved(env,tmp_path)
    before=snap(env)
    with TestClient(create_app(env[0],replace(env[1],run_seconds=30)),headers={'Authorization':'Bearer synthetic-test-A'}) as client:
        r=client.post(f'/api/projects/{env[5]}/conditional-apps/{named["id"]}/manifest-preview',json={'expected_app_fingerprint':named['fingerprint'],'request_key':'tightened'})
        assert r.status_code in {400,409},r.text
    assert snap(env)==before

@pytest.mark.parametrize('ref',[6,7])
def test_current_source_and_target_revocation_failclosed(env,tmp_path,ref):
    from sim2act.db import grants,projects
    app,_,_=promote(env,tmp_path)
    with env[0].tx() as c:
        runtime=c.execute(select(projects.c.runtime_id).where(projects.c.id==env[5])).scalar_one()
        grant=c.execute(select(grants).where(grants.c.project_id==env[5],grants.c.principal_id==runtime,grants.c.resource_id==env[ref],grants.c.tool_ref=='resource.read')).mappings().one()
        c.execute(update(grants).where(grants.c.id==grant['id']).values(revoked=True,revision=grant['revision']+1))
    before=snap(env)
    r=env[2].get(f'/api/projects/{env[5]}/apps/{app["id"]}')
    assert r.status_code==403,r.text
    r=env[2].post(f'/api/projects/{env[5]}/apps/{app["id"]}/previews',json={'expected_candidate_fingerprint':app['fingerprint'],'input':scenario(),'request_key':'revoked'})
    assert r.status_code==403,r.text
    assert snap(env)==before

def test_authenticated_other_owner_and_wrong_project_cannot_use_app(env,tmp_path):
    app,_,_=promote(env,tmp_path);before=snap(env)
    path=f'/api/projects/{env[5]}/apps/{app["id"]}'
    env[2].headers.update({'Authorization':'Bearer synthetic-test-B'})
    assert env[2].get('/api/apps/'+app['id']).status_code==403
    assert env[2].post(path+'/previews',json={'expected_candidate_fingerprint':app['fingerprint'],'input':scenario(),'request_key':'other-owner'}).status_code==403
    env[2].headers.update({'Authorization':'Bearer synthetic-test-A'})
    assert env[2].get('/api/projects/proj_'+'0'*32+'/apps/'+app['id']).status_code==403
    assert snap(env)==before

def test_default_provider_remains_zero_send_and_same_key_recovers(env,tmp_path):
    from sim2act.db import attempts
    from sim2act.worker import Worker
    app,_,_=promote(env,tmp_path)
    path=f'/api/projects/{env[5]}/apps/{app["id"]}/previews'
    body={'expected_candidate_fingerprint':app['fingerprint'],'input':scenario(),'request_key':'no-provider'}
    accepted=env[2].post(path,json=body);assert accepted.status_code==202
    with env[0].tx() as c:before=c.execute(select(attempts.c.id)).scalars().all()
    assert Worker(env[0],env[1]).once()
    with env[0].tx() as c:
        after=c.execute(select(attempts.c.id)).scalars().all()
        run=c.execute(select(runs).where(runs.c.id==accepted.json()['run_id'])).mappings().one()
    assert after==before and run['status']=='WAITING_RESOURCE'
    assert env[2].post(path,json=body).json()['run_id']==run['id']

def test_private_manifest_rejected_by_legacy_preview_and_internal_release(env,tmp_path):
    app,_,_=promote(env,tmp_path);before=snap(env)
    r=env[2].post('/api/apps/'+app['id']+'/previews',json={'input':scenario(),'request_key':'legacy-preview'})
    assert r.status_code in {400,403,409},r.text
    r=env[2].get('/api/internal/apps/'+app['id']+'/releases')
    assert r.status_code in {400,403,409},r.text
    assert snap(env)==before
