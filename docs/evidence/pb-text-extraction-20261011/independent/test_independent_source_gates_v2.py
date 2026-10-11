"""Independent finite source-gate probes; synthetic initial model, actual SQLite/API.

No repository edits. Kept separate from maintained regression nodes and page controls.
"""
import copy
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import delete, insert, select, update
from test_registered_text_extraction import prepared, request, snapshot

from sim2act.db import app_drafts, attempts, fingerprint, internal_app_runs, new_id, operations, task_extractions

OUT=Path('/tmp/pb-text-extraction-review-20261011')

@pytest.mark.parametrize('fault',['source-generation-response','source-generation-raw','source-generation-unknown','source-app-error','selected-attempt-started','marker-deleted','source-generation-marker-deleted'])
def test_independent_exact_source_and_marker_gates(env,fault):
    data,source_app,_,instance,source,target,_,url=prepared(env)
    _,body=request(data,url,target)
    accepted=data[2].post(url+'/extract',json=body)
    assert accepted.status_code==201,accepted.text
    made=accepted.json()
    with data[0].tx() as c:
        raw_source=c.execute(select(app_drafts).where(app_drafts.c.id==source_app)).mappings().one()
        origin=raw_source['candidate']['goal_application']['run_id']
        if fault=='source-generation-response':
            attempt=c.execute(select(attempts).where(attempts.c.run_id==origin).order_by(attempts.c.created_at)).mappings().first()
            response=copy.deepcopy(attempt['response']);response['tool_calls'][0]['function']['arguments']=json.dumps({'resource_id':'res_wrong'})
            c.execute(update(attempts).where(attempts.c.id==attempt['id']).values(response=response))
        elif fault=='source-generation-raw':
            attempt=c.execute(select(attempts).where(attempts.c.run_id==origin).order_by(attempts.c.created_at)).mappings().first()
            parameters=copy.deepcopy(attempt['parameters']);parameters['generation_received_raw']={'controlled':'wrong exact raw'}
            c.execute(update(attempts).where(attempts.c.id==attempt['id']).values(parameters=parameters))
        elif fault=='source-generation-unknown':
            c.execute(insert(operations).values(id=new_id('op'),run_id=origin,call_id='independent_unknown',fingerprint=fingerprint({'tool':'resource.read','args':{}}),tool_ref='resource.read',status='OUTCOME_UNKNOWN'))
        elif fault=='source-app-error':
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id==source['app_run_id']).values(error={'code':'controlled'}))
        elif fault=='selected-attempt-started':
            c.execute(insert(attempts).values(id=new_id('attempt'),run_id=source['id'],status='STARTED'))
        elif fault=='marker-deleted':
            c.execute(delete(task_extractions).where(task_extractions.c.app_id==made['id']))
        else:
            from sim2act.db import goal_application_candidates
            c.execute(delete(goal_application_candidates).where(goal_application_candidates.c.app_id==source_app))
    before=snapshot(data[0]);replies=[]
    routes=[('POST',url+'/extract',{**body,'request_key':'independent-new-after-fault'}),('POST',url+'/extract',body),('GET',url+'/extraction-receipts?request_key='+body['request_key'],None),('GET','/api/apps/'+made['id'],None)]
    if fault=='marker-deleted':routes=routes[2:]
    for method,path,payload in routes:
        response=data[2].request(method,path,json=payload)
        replies.append({'method':method,'path':path,'status':response.status_code,'text':response.text})
    assert snapshot(data[0])==before
    p=OUT/(os.environ.get('PB_GATE_PREFIX','candidate2-independent-source-')+fault+'.json')
    if p.exists():raise AssertionError('Refusing overwrite')
    p.write_text(json.dumps({'fault':fault,'responses':replies,'classification':'ACTUAL_SQLITE_API_SYNTHETIC_GENERATION_SOURCE','real_model':'NOT_RUN'},ensure_ascii=False,indent=2)+'\n')
    assert all(r['status'] in {400,403,409} for r in replies),replies
