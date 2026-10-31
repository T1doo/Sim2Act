"""Budget rejection is a successful negative diagnostic, never goal success."""
import importlib.util
import json
from pathlib import Path

import pytest
from sim2act.db import fingerprint

spec=importlib.util.spec_from_file_location('ordinary30_diagnostic',
    Path(__file__).resolve().parents[1]/'scripts/diagnose_ordinary_thirty.py')
diagnostic=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def saved_state(status='REJECTED_KNOWN'):
    response={'output':'synthetic finite reply','usage':{'tokens':3}}
    run=dict(id='synthetic-run',status='RUNNING',result='null')
    attempt=dict(run_id=run['id'],status=status,parameters=json.dumps({'natural_spec':{'operation_id':'model'}}),
        response=json.dumps(response),usage=json.dumps({'status':'known','tokens':{'total_tokens':3}}))
    operation=dict(id='model',run_id=run['id'],status='DISPATCHED' if status=='RECEIVED' else status,receipt='null')
    app=dict(output='null',result_version=None)
    events=[dict(kind='NS_RECEIVED',data={'response_fingerprint':fingerprint(response)}),
        dict(kind='SPEC_STEP_VERIFIED',data={'operation_id':'earlier-read'})]
    if status=='REJECTED_KNOWN':events.append(dict(kind='NS_REJECTED',data={'error':'BUDGET_EXHAUSTED'}))
    failures=[dict(run_id=run['id'],error=dict(code='BUDGET_EXHAUSTED',message='Finite model settlement interval ended'))]
    return [run,attempt,operation,app,0,events,failures]


@pytest.mark.parametrize('status',['RECEIVED','REJECTED_KNOWN'])
def test_original_budget_boundaries_with_retained_known_usage(status):
    state=saved_state(status)
    assert diagnostic.validate_negative_state(*state)=={'status':'known','tokens':{'total_tokens':3}}


@pytest.mark.parametrize('damage',['other-error','other-run','lost-usage','lost-response',
    'response-changed','wrong-operation','fake-success','model-settled','typed-result','result-version','saved-output'])
def test_diagnostic_refuses_unrelated_error_or_any_goal_commit(damage):
    state=saved_state('RECEIVED')
    run,attempt,operation,app,_,events,failures=state
    if damage=='other-error':failures[0]['error']['code']='VERSION_CONFLICT'
    if damage=='other-run':failures[0]['run_id']='other'
    if damage=='lost-usage':attempt['usage']='{"status":"unknown"}'
    if damage=='lost-response':attempt['response']='null'
    if damage=='response-changed':attempt['response']='{"output":"different"}'
    if damage=='wrong-operation':operation['id']='earlier-read'
    if damage=='fake-success':run['status']='SUCCEEDED'
    if damage=='model-settled':events.append(dict(kind='NS_SETTLED',data={}))
    if damage=='typed-result':state[4]=1
    if damage=='result-version':app['result_version']=1
    if damage=='saved-output':app['output']='{"result":"saved"}'
    with pytest.raises(AssertionError):diagnostic.validate_negative_state(*state)
