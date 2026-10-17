"""Successive bindings use the actual original Worker and synthetic CSV only."""
import json

import pytest
from sqlalchemy import func, select, text
from test_csv_goal_revisions import approve, drive, ready, start
from test_csv_goal_revisions import raw_trace as raw_trace
from test_internal_lifecycle import limits

from sim2act import app_jobs as jobs
from sim2act import csv_column_revisions as successive
from sim2act.db import Store, grants, internal_instances, principals, run_contracts


def adopt(data,instance,path,value,version):
    body=dict(request_key=value["request_key"],expected_revision=instance["revision"],
        target_release_id=version["id"],expected_target_fingerprint=version["fingerprint"])
    r=data[2].post(path+"/adoption-approvals",json=body)
    assert r.status_code==201,r.text
    a=data[2].get(path+"/adoption-approvals/"+value["request_key"])
    assert a.status_code==200,a.text
    r=data[2].post(f"/api/internal/instances/{instance['id']}/switch-approvals/{a.json()['id']}/commit",json=dict(fingerprint=a.json()["fingerprint"]))
    assert r.status_code==200,r.text
    return data[2].get(f"/api/internal/instances/{instance['id']}").json()


def adopted(env):
    data,aid,base,instance,path,body,value,goal=ready(env,prior=True)
    checked=start(data,path,value)
    drive(data,checked["run_id"])
    version=approve(data,path,value)
    current=adopt(data,instance,path,value,version)
    second=jobs.enqueue(data[0],data[3],instance["id"],current["revision"],version["fingerprint"],
        {"column":"quantity"},"v2-business-result",limits(data),csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    drive(data,second["run_id"])
    current=data[2].get(f"/api/internal/instances/{instance['id']}").json()
    return data,aid,base,current,path,value,version,goal,second


def immutable_rows(data):
    """Capture actual stored JSON strings, including old acceptance seals."""
    tables=("app_drafts","internal_releases","run_contracts","internal_run_bindings",
        "internal_app_runs","internal_instance_data","operations","internal_owner_records",
        "csv_owner_records","delivery_graph_requests","goal_card_versions")
    with data[0].tx() as c:
        return {name:[dict(r) for r in c.execute(text('SELECT * FROM '+name)).mappings()] for name in tables}


def assert_preserved(data,before):
    after=immutable_rows(data)
    for name,rows in before.items():
        assert all(row in after[name] for row in rows),(name,rows,after[name])


def proposal(data,current,path,key="successive-one"):
    r=data[2].get(path+"/context")
    assert r.status_code==200,r.text
    ctx=r.json()
    body=dict(request_key=key,expected_revision=current["revision"],
        expected_release_fingerprint=current["release_fingerprint"],expected_graph_fingerprint=ctx["graph_fingerprint"],
        goal_version=ctx["goal"]["version"],goal_fingerprint=ctx["goal"]["fingerprint"],
        baseline_column=ctx["parent"]["column"],column="amount")
    r=data[2].post(path+"/previews",json=body)
    assert r.status_code==201,r.text
    return body,r.json()


@pytest.mark.parametrize("goal_mode",["same","next"])
def test_current_effective_parent_actual_check_release_adopt_and_new_result(env,tmp_path,goal_mode):
    data,aid,base,current,path,old_value,v2,goal,second=adopted(env)
    before=immutable_rows(data)
    with data[0].tx() as c:
        counts={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    cid=old_value["context"]["goal"]["card_id"]
    if goal_mode=="next":
        r=data[2].put('/api/goal-cards/'+cid,json={**goal,"goal":"明确下一目标：汇总 amount，保留同一材料","expected_version":2})
        assert r.status_code==200,r.text
    body,value=proposal(data,current,path)
    assert value["namespace"]==successive.VERSION
    assert value["context"]["parent"]["effective_fingerprint"]==old_value["effective_fingerprint"]
    assert value["context"]["parent"]["spec_revision"]==2 and value["spec_revision"]==3
    assert value["context"]["goal"]["version"]==(2 if goal_mode=="same" else 3)
    assert value["context"]["goal_mode"]==("KEEP_ADOPTED_GOAL" if goal_mode=="same" else "EXPLICIT_NEXT_GOAL")
    assert value["effective_candidate"]["manifest"]["revision"]==3
    assert value["effective_candidate"]["manifest"]["action_bindings"][0]["revision"]==3
    assert value["effective_candidate"]["generation"]==base["snapshot"]["draft"]["candidate"]["generation"]
    accepted=start(data,path,value)
    # A parent SOURCE may only create this accepted isolated CHECK, never a
    # new business instance or a new revision from the CHECK itself.
    denied=data[2].post(f"/api/internal/releases/{v2['id']}/instances",json=dict(expected_release_fingerprint=v2["fingerprint"],request_key="not-a-check"))
    assert denied.status_code==400 and denied.json()["error"]["code"]=="UNSUPPORTED_CAPABILITY"
    check_path=f"/api/internal/instances/{accepted['check_instance_id']}/csv-goal-revisions/context"
    assert data[2].get(check_path).status_code==409
    drive(data,accepted["run_id"])
    version=approve(data,path,value)
    assert version["snapshot"]["draft"]==base["snapshot"]["draft"]
    assert version["snapshot"]["csv_goal_revision_source"]["parent"]["release_id"]==v2["id"]
    adopted_state=adopt(data,current,path,value,version)
    assert adopted_state["id"]==current["id"] and adopted_state["revision"]==3
    assert adopted_state["data_version"]==current["data_version"]==2
    fresh=jobs.enqueue(data[0],data[3],current["id"],3,version["fingerprint"],{"column":"amount"},
        "v3-business-result",limits(data),csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    drive(data,fresh["run_id"])
    result=jobs.inspect_job(data[0],data[3],fresh["run_id"])
    assert result["result"]["sum"]=="30" and result["result_version"]==3
    assert result["id"]!=data[2].csv_previous_run["run_id"] and result["release_id"]==version["id"]
    pending=data[2].get(f"/api/internal/instances/{current['id']}/runs/{fresh['run_id']}/csv-owner-review")
    assert pending.status_code==200 and pending.json()["owner_acceptance"]=="PENDING"
    for old in (data[2].csv_previous_run,second):
        assert data[2].get(f"/api/internal/instances/{current['id']}/runs/{old['run_id']}").status_code==200
    for release in (base,v2):
        assert data[2].get('/api/internal/releases/'+release["id"]).status_code==200
    assert_preserved(data,before)
    with data[0].tx() as c:
        assert counts=={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
        frozen=c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==fresh["run_id"])).scalar_one()
        actual=c.execute(select(internal_instances).where(internal_instances.c.id==current["id"])).mappings().one()
    assert frozen["goal"]["goal"]==value["context"]["goal"]["snapshot"]["content"]["goal"]
    (tmp_path/'actual-successive-delivery.json').write_text(json.dumps(dict(goal_mode=goal_mode,old_value=old_value,
        proposal=value,checked=accepted,parent=v2,version=version,new_run=result,contract=frozen,
        instance=dict(actual),pending=pending.json(),unchanged_counts=counts),ensure_ascii=False,indent=2))


@pytest.mark.parametrize("case",["same-navigation","next-unknown","navigation"])
def test_visible_current_effective_revision_and_fenced_recovery(env,tmp_path,case):
    import os
    import subprocess
    import threading
    from pathlib import Path

    from test_internal_lifecycle import create

    data,aid,base,current,path,old_value,v2,goal,second=adopted(env)
    other=data[2].post('/api/projects',json={"name":"Other owned project"}).json()["id"]
    instance2=create(data,base)
    data[0].project(data[4],"Other account project")
    before=immutable_rows(data)
    with data[0].tx() as c:
        counts={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    info=dict(case=case,project=data[5],other=other,app=aid,instance=current["id"],
        instance2=instance2["id"],release=v2["id"],output=str(tmp_path/'page-result.json'))
    (tmp_path/'info.json').write_text(json.dumps(info))
    process=watchdog=None
    try:
        with (tmp_path/'node.stderr').open('w') as errors:
            process=subprocess.Popen(['node','tests/csv_column_revision.cjs',str(tmp_path/'info.json')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,
                env={**os.environ,'NODE_PATH':str(Path.cwd()/'scripts/engineering-ci/node_modules')})
            # Multiple actual frozen-parent reads are intentionally retained.
            # This is a fixture watchdog, not a changed application deadline.
            watchdog=threading.Timer(900,process.kill)
            watchdog.start()
            for line in process.stdout:
                request=json.loads(line)
                if request.get('done'):
                    break
                if request.get('command')=='worker':
                    drive(data,request['run'])
                    answer=dict(status=200,text='{}')
                elif request.get('command')=='proof':
                    reopened=Store(data[1].database_url,test_only=True)
                    try:
                        new=jobs.inspect_job(reopened,data[3],request['run'])
                    finally:
                        reopened.engine.dispose()
                    assert new['id']==request['run'] and new['id'] not in (data[2].csv_previous_run['run_id'],second['run_id'])
                    assert new['result']['sum']=='30' and new['result_version']==3 and new['instance_id']==current['id']
                    assert new['release_id'] not in (base['id'],v2['id'])
                    assert new['known_effects'][0]['run_id']==new['app_run_id']
                    assert jobs.inspect_job(data[0],data[3],second['run_id'])['result']['sum']=='5'
                    assert jobs.inspect_job(data[0],data[3],data[2].csv_previous_run['run_id'])['result']['sum']=='30'
                    with data[0].tx() as c:
                        frozen=c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==request['run'])).scalar_one()
                        actual=c.execute(select(internal_instances).where(internal_instances.c.id==current['id'])).mappings().one()
                    assert actual['revision']==3 and actual['data_version']==3 and frozen['runtime_id']==current['runtime_id']
                    expected='明确下一目标：汇总 amount，保留同一材料' if case=='next-unknown' else goal['goal']
                    assert frozen['goal']['goal']==expected
                    assert_preserved(data,before)
                    (tmp_path/'actual-browser-delivery.json').write_text(json.dumps(dict(
                        new=new,contract=frozen,instance=dict(actual),old_value=old_value,parent=v2,unchanged_counts=counts),ensure_ascii=False,indent=2))
                    answer=dict(status=200,text='{}')
                else:
                    response=data[2].request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                    answer=dict(status=response.status_code,text=response.text,content_type=response.headers.get('content-type'))
                process.stdin.write(json.dumps(dict(id=request['id'],**answer))+'\n')
                process.stdin.flush()
            process.stdin.close()
            code=process.wait(timeout=15)
        assert code==0,(tmp_path/'node.stderr').read_text()
        page=json.loads((tmp_path/'page-result.json').read_text())
        assert page['status']=='PASS',page
        with data[0].tx() as c:
            assert counts=={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
