"""Synthetic real-HTTP/JSDOM material UI checks; existing NoModel Worker only."""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest
from conftest import env as env
from sqlalchemy import func, insert, select
from test_csv_column_revisions import adopt, assert_preserved, immutable_rows
from test_csv_goal_revisions import approve, drive, ready, start
from test_csv_goal_revisions import raw_trace as raw_trace
from test_internal_lifecycle import create

from sim2act import app_jobs as jobs
from sim2act.db import (
    Store,
    grants,
    internal_instances,
    new_id,
    principals,
    run_contracts,
)


def material_fixture(env):
    data,aid,base,instance,path,body,value,goal=ready(env,prior=True)
    checked=start(data,path,value)
    drive(data,checked["run_id"])
    version=approve(data,path,value)
    current=adopt(data,instance,path,value,version)
    response=data[2].post(f"/api/projects/{data[5]}/resources",json=dict(
        name="explicit target B.csv",format="csv",content="amount,quantity\n1.20,7\n2.35,11\n"))
    assert response.status_code==201,response.text
    rid=response.json()["id"]
    # Fixture-only exact existing authorization, before the no-new-Grants baseline.
    # The production replacement path must never add these grants itself.
    with data[0].tx() as c:
        for tool in ("resource.read","data.aggregate_csv"):
            c.execute(insert(grants).values(id=new_id("grant"),principal_id=current["runtime_id"],
                project_id=data[5],resource_id=rid,tool_ref=tool,expires_at=time.time()+86400,
                revision=1,revoked=False))
    return data,aid,base,current,path,value,version,goal,rid


@pytest.mark.parametrize("case",["flow-recovery","navigation"])
def test_visible_material_replacement_actual_http_and_fenced_recovery(env,tmp_path,case):
    data,aid,base,current,path,old_value,v2,goal,rid=material_fixture(env)
    other=data[2].post('/api/projects',json={"name":"Other owned project"}).json()["id"]
    instance2=create(data,base)
    data[0].project(data[4],"Other account project")
    # New authorized fixture resources alter the real graph authority fingerprint.
    # Refresh via the existing explicit derive before the immutable baseline.
    refreshed=data[2].post(f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive",json=dict(
        request_key="material-ui-current-baseline",expected_candidate_fingerprint=base["snapshot"]["draft"]["fingerprint"]))
    assert refreshed.status_code==201,refreshed.text
    before=immutable_rows(data)
    with data[0].tx() as c:
        counts={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    info=dict(case=case,project=data[5],other=other,app=aid,instance=current["id"],
        instance2=instance2["id"],release=v2["id"],sourceA=data[6],material=rid,
        hashA=hashlib.sha256(b"amount,quantity\n10,2\n20,3\n").hexdigest(),
        hashB=hashlib.sha256(b"amount,quantity\n1.20,7\n2.35,11\n").hexdigest(),
        dataVersion=current["data_version"],output=str(tmp_path/'page-result.json'))
    (tmp_path/'info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    process=watchdog=None
    try:
        with (tmp_path/'node.stderr').open('w') as errors:
            process=subprocess.Popen(['node',str(Path(__file__).with_name('csv_material_revision.cjs')),str(tmp_path/'info.json')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,
                env={**os.environ,'NODE_PATH':str(Path.cwd()/'scripts/engineering-ci/node_modules')})
            watchdog=threading.Timer(600,process.kill)
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
                        old=jobs.inspect_job(reopened,data[3],data[2].csv_previous_run['run_id'])
                    finally:
                        reopened.engine.dispose()
                    assert new['id']==request['run'] and new['id']!=old['id']
                    assert new['result']['sum']=='18' and new['result']['count']==2
                    assert new['result_version']==current['data_version']+1 and new['instance_id']==current['id']
                    assert new['release_id'] not in (base['id'],v2['id'])
                    assert new['known_effects'][0]['run_id']==new['app_run_id']
                    assert old['result']['sum']=='30' and old['release_id']==base['id']
                    with data[0].tx() as c:
                        frozen=c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==request['run'])).scalar_one()
                        actual=c.execute(select(internal_instances).where(internal_instances.c.id==current['id'])).mappings().one()
                    assert actual['revision']==current['revision']+1 and actual['data_version']==current['data_version']+1
                    assert frozen['runtime_id']==current['runtime_id'] and frozen['goal']['goal']==goal['goal']
                    assert frozen['goal']['resource_refs']==[rid]
                    assert frozen['resources'][0]['resource_id']==rid and frozen['resources'][0]['content_hash']==info['hashB']
                    assert_preserved(data,before)
                    (tmp_path/'actual-browser-delivery.json').write_text(json.dumps(dict(
                        new=new,old=old,contract=frozen,instance=dict(actual),original_proposal=old_value,
                        parent=v2,unchanged_counts=counts),ensure_ascii=False,indent=2))
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
        assert_preserved(data,before)
        with data[0].tx() as c:
            assert counts=={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
