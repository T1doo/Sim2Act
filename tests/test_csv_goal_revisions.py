"""Synthetic same-app Goal v2 -> actual original NoModel Worker -> CAS adoption."""
import copy
import json
import re

import pytest
from sqlalchemy import delete, event, func, select, update
from test_goal_candidates import create_candidate, setup_card
from test_internal_lifecycle import create, limits, release
from test_persistent_app_runs import NoModel

from sim2act import app_jobs as jobs
from sim2act import csv_goal_revisions as revision
from sim2act.db import (
    Store,
    app_drafts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instances,
    internal_run_bindings,
    operations,
    principals,
    run_contracts,
    runs,
)
from sim2act.worker import Worker


@pytest.fixture(autouse=True)
def raw_trace(env,tmp_path):
    client = env[2]
    original = client.request
    trace = []
    def request(method,url,**kwargs):
        response = original(method,url,**kwargs)
        trace.append(dict(method=method,path=str(url),body=kwargs.get("json"),status=response.status_code,
            response=response.json() if response.headers.get("content-type","").startswith("application/json") else None))
        return response
    client.request = request
    yield
    (tmp_path / "actual-http.json").write_text(json.dumps(trace,ensure_ascii=False,indent=2))
    client.request = original


def baseline(env):
    client = env[2]
    rid = client.post(f"/api/projects/{env[5]}/resources",json=dict(name="two.csv",format="csv",
        content="amount,quantity\n10,2\n20,3\n")).json()["id"]
    data = (*env[:-1],rid)
    cid,content = setup_card(data)
    candidate = create_candidate(data,cid)
    assert candidate.status_code == 201,candidate.text
    aid = candidate.json()["id"]
    app = client.get("/api/apps/"+aid).json()
    base,_,_ = release(data,aid,app["fingerprint"])
    instance = create(data,base)
    return data,aid,base,instance,cid,content,app


def ready(env,*,prior=False):
    data,aid,base,instance,cid,content,app = baseline(env)
    client = env[2]
    if prior:
        from test_csv_owner_review import choices, endpoint, prepare_review
        old = jobs.enqueue(data[0],data[3],instance["id"],instance["revision"],base["fingerprint"],
            {"column":"amount"},"old-v1-accepted",limits(data),csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
        drive(data,old["run_id"])
        _,prepared,_ = prepare_review(data,instance,old["run_id"])
        accepted = client.post(endpoint(instance,old["run_id"])+"-requests",json=choices(prepared))
        assert accepted.status_code == 201,accepted.text
        client.csv_previous_run = old
    updated = {**content,"title":"数量 Goal v2","goal":"明确改为汇总 quantity，保留原材料与历史"}
    r = client.put(f"/api/goal-cards/{cid}",json={**updated,"expected_version":1})
    assert r.status_code == 200,r.text
    r = client.post(f"/api/projects/{env[5]}/apps/{aid}/delivery-graph/derive",json=dict(
        request_key="baseline",expected_candidate_fingerprint=app["fingerprint"]))
    assert r.status_code == 201,r.text
    path = f"/api/internal/instances/{instance['id']}/csv-goal-revisions"
    ctx = client.get(path+"/context")
    assert ctx.status_code == 200,ctx.text
    ctx = ctx.json()
    body = dict(request_key="revision-one",expected_revision=instance["revision"],
        expected_release_fingerprint=base["fingerprint"],expected_graph_fingerprint=ctx["graph_fingerprint"],
        goal_version=2,goal_fingerprint=ctx["goal"]["fingerprint"],baseline_column="amount",column="quantity")
    r = client.post(path+"/previews",json=body)
    assert r.status_code == 201,r.text
    return data,aid,base,instance,path,body,r.json(),updated


def start(data,path,value):
    body = dict(request_key=value["request_key"],expected_preview_fingerprint=value["preview_fingerprint"],consent=revision.CHECK_CONSENT)
    r = data[2].post(path+"/checks",json=body)
    assert r.status_code == 202,r.text
    assert data[2].post(path+"/checks",json=body).json() == r.json()
    return r.json()


def drive(data,jid):
    cold = Store(data[1].database_url,test_only=True)
    try:
        worker = Worker(cold,data[1],NoModel())
        for _ in range(5):
            worker.once()
            with cold.tx() as c:
                row = c.execute(select(runs.c.status,runs.c.error).where(runs.c.id == jid)).mappings().one()
            if row["status"] == "SUCCEEDED":
                return
            assert row["status"] not in {"FAILED","WAITING_RESOURCE"},row
        raise AssertionError(row)
    finally:
        cold.engine.dispose()


def approve(data,path,value):
    r = data[2].get(path+"/checks/"+value["request_key"])
    assert r.status_code == 200,r.text
    proof = r.json()
    assert proof["status"] == "PASS"
    r = data[2].post(path+"/version-approvals",json=dict(request_key=value["request_key"],
        expected_check_fingerprint=proof["check_fingerprint"],consent=revision.VERSION_CONSENT))
    assert r.status_code == 201,r.text
    a = r.json()
    r = data[2].post(f"/api/internal/approvals/{a['id']}/commit",json=dict(fingerprint=a["fingerprint"]))
    assert r.status_code == 200,r.text
    return r.json()


def test_same_app_actual_check_explicit_release_adoption_and_new_goal_run(env):
    data,aid,base,instance,path,body,value,updated = ready(env)
    original = copy.deepcopy(base)
    with data[0].tx() as c:
        counts = {t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    assert data[2].get(path+"/previews/"+body["request_key"]).json() == value
    assert value["effective_candidate"]["generation"] == base["snapshot"]["draft"]["candidate"]["generation"]
    assert value["effective_candidate"]["goal"] == updated
    started = start(data,path,value)
    drive(data,started["run_id"])
    with data[0].tx() as c:
        frozen = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == started["run_id"])).scalar_one()
        assert frozen["goal"]["goal"] == updated["goal"]
    version = approve(data,path,value)
    assert version["snapshot"]["draft"] == base["snapshot"]["draft"]
    assert version["snapshot"][revision.SOURCE]["reference"]["purpose"] == "USE"
    restored = data[2].get(f"/api/internal/releases/{base['id']}").json()
    assert all(restored[k] == v for k,v in original.items())
    old = jobs.enqueue(data[0],data[3],instance["id"],instance["revision"],base["fingerprint"],
        {"column":"amount"},"before-adoption",limits(data))
    drive(data,old["run_id"])
    assert jobs.inspect_job(data[0],data[3],old["run_id"])["result"]["sum"] == "30"
    # Old instance data changed: the already checked proposal cannot be adopted.
    r = data[2].post(f"/api/internal/instances/{instance['id']}/switch-approvals",json=dict(
        expected_revision=instance["revision"],target_release_id=version["id"],expected_target_fingerprint=version["fingerprint"]))
    assert r.status_code == 409,r.text
    with data[0].tx() as c:
        assert {t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)} == counts
        assert c.execute(select(app_drafts.c.fingerprint).where(app_drafts.c.id == aid)).scalar() == base["snapshot"]["draft"]["fingerprint"]


def test_adopt_without_drift_new_worker_result_and_new_run_pending(env,tmp_path):
    data,aid,base,instance,path,body,value,updated = ready(env,prior=True)
    started = start(data,path,value)
    drive(data,started["run_id"])
    version = approve(data,path,value)
    r = data[2].post(f"/api/internal/instances/{instance['id']}/switch-approvals",json=dict(
        expected_revision=instance["revision"],target_release_id=version["id"],expected_target_fingerprint=version["fingerprint"]))
    assert r.status_code == 201,r.text
    a = r.json()
    r = data[2].post(f"/api/internal/instances/{instance['id']}/switch-approvals/{a['id']}/commit",json=dict(fingerprint=a["fingerprint"]))
    assert r.status_code == 200,r.text
    inst = r.json()
    accepted = jobs.enqueue(data[0],data[3],instance["id"],inst["revision"],version["fingerprint"],
        {"column":"quantity"},"after-adoption",limits(data),csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    drive(data,accepted["run_id"])
    result = jobs.inspect_job(data[0],data[3],accepted["run_id"])
    assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "5"
    assert result["instance_id"] == instance["id"] and result["release_id"] == version["id"]
    state = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}/csv-owner-review")
    assert state.status_code == 200,state.text
    assert state.json()["owner_acceptance"] == "PENDING",state.json()
    previous = jobs.inspect_job(data[0],data[3],data[2].csv_previous_run["run_id"])
    assert previous["result"]["sum"] == "30" and previous["release_id"] == base["id"]
    assert result["result_version"] == 2
    bad = jobs.enqueue(data[0],data[3],instance["id"],inst["revision"],version["fingerprint"],
        {"column":"amount"},"old-column-rejected",limits(data))
    assert Worker(data[0],data[1],NoModel()).once()
    invalid=jobs.inspect_job(data[0],data[3],bad["run_id"])
    assert invalid["status"] == "FAILED" and invalid["result"] is None
    with data[0].tx() as c:
        assert c.execute(select(operations.c.id).where(operations.c.run_id == bad["run_id"])).first() is None
    with data[0].tx() as c:
        frozen = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == accepted["run_id"])).scalar_one()
    (tmp_path/"actual-delivery.json").write_text(json.dumps(dict(old_run=previous,new_run=result,contract=frozen,
        version=version,owner_state=state.json()),ensure_ascii=False,indent=2))
    # Goal v3 invalidates NEW work, while both frozen v1/v2 histories remain readable.
    cid = value["context"]["goal"]["card_id"]
    assert data[2].put(f"/api/goal-cards/{cid}",json={**updated,"goal":"Goal v3 未经新重验","expected_version":2}).status_code == 200
    assert data[2].get(f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}").status_code == 200
    r = data[2].post(f"/api/internal/instances/{instance['id']}/runs",json=dict(
        expected_revision=inst["revision"],expected_release_fingerprint=version["fingerprint"],input={"column":"quantity"},request_key="head-v3"))
    assert r.status_code == 409,r.text
    # The immutable SOURCE Release still identifies USE if every Run marker
    # group is stripped and the ordinary request/body hashes are re-signed.
    with data[0].tx() as c:
        s=copy.deepcopy(c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id==accepted["run_id"])).scalar_one())
        s.pop(revision.MARKER)
        request={k:s[k] for k in ("instance_id","expected_revision","expected_release_fp","input","csv_review")}
        s["request_fingerprint"]=fingerprint(request)
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==accepted["run_id"]).values(snapshot=s,fingerprint=fingerprint(s)))
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==s["app_run_id"]).values(fingerprint=s["request_fingerprint"]))
        ctx=copy.deepcopy(c.execute(select(runs.c.context).where(runs.c.id==accepted["run_id"])).scalar_one())
        ctx.pop(revision.MARKER)
        c.execute(update(runs).where(runs.c.id==accepted["run_id"]).values(context=ctx,fingerprint=fingerprint(s)))
        c.execute(delete(events).where(events.c.run_id==accepted["run_id"],events.c.kind=="CSV_GOAL_REVISION_FROZEN"))
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==accepted["run_id"],
            delivery_graph_requests.c.kind.in_([revision.JOB,revision.JOB+"_seal"])))
    assert data[2].get(f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}").status_code == 409


@pytest.mark.parametrize("fault",["goal","permission","instance","lock"])
def test_checked_proposal_rejects_current_drift_and_keeps_original(env,fault):
    data,aid,base,instance,path,body,value,updated = ready(env)
    accepted = start(data,path,value)
    drive(data,accepted["run_id"])
    proof = data[2].get(path+"/checks/"+body["request_key"]).json()
    if fault == "goal":
        cid = value["context"]["goal"]["card_id"]
        assert data[2].put(f"/api/goal-cards/{cid}",json={**updated,"goal":"next","expected_version":2}).status_code == 200
    elif fault == "permission":
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.project_id == data[5],grants.c.resource_id == data[6]).values(revoked=True))
    elif fault == "instance":
        old = jobs.enqueue(data[0],data[3],instance["id"],instance["revision"],base["fingerprint"],{"column":"amount"},"changed-data",limits(data))
        drive(data,old["run_id"])
    else:
        node = next(n for n in value["baseline_graph"]["graph"]["nodes"] if n["key"] == "action:aggregate")
        r = data[2].post(f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/manual-locks",json=dict(
            request_key="lock",expected_graph_fingerprint=value["context"]["graph_fingerprint"],
            expected_graph_revision=value["context"]["graph_revision"],expected_lock_revision=0,
            consent="CONFIRM_EXACT_PROJECT_EDIT_LOCK",
            change=dict(node_id=node["id"],expected_revision=node["revision"],expected_content_fingerprint=node["content_fingerprint"]),locked=True))
        assert r.status_code == 201,r.text
    r = data[2].post(path+"/version-approvals",json=dict(request_key=body["request_key"],
        expected_check_fingerprint=proof["check_fingerprint"],consent=revision.VERSION_CONSENT))
    assert r.status_code in {403,409},r.text
    with data[0].tx() as c:
        assert c.execute(select(internal_instances.c.release_id).where(internal_instances.c.id == instance["id"])).scalar() == base["id"]


def test_check_role_pins_wrong_input_and_independent_marker_downgrade(env):
    data,aid,base,instance,path,body,value,updated = ready(env)
    accepted = start(data,path,value)
    check_iid = accepted["check_instance_id"]
    private=[]
    def observe(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith("SELECT") and "runs.goal," in statement and "FROM runs" in statement:
            private.append(statement)
    event.listen(data[0].engine,"before_cursor_execute",observe)
    try:
        assert data[2].get(f"/api/internal/instances/{check_iid}/runs/{accepted['run_id']}").status_code == 200
    finally:
        event.remove(data[0].engine,"before_cursor_execute",observe)
    assert private,"positive SQL control must see a protected full Run read"
    private.clear()
    # Neither no-op switching nor another normal Run may consume CHECK identity.
    assert data[2].post(f"/api/internal/instances/{check_iid}/switch-approvals",json=dict(expected_revision=1,
        target_release_id=base["id"],expected_target_fingerprint=base["fingerprint"])).status_code == 409
    assert data[2].post(f"/api/internal/instances/{check_iid}/runs",json=dict(expected_revision=1,
        expected_release_fingerprint=base["fingerprint"],input={"column":"quantity"},request_key="pollute")).status_code == 409
    # Removing start receipts still leaves binding/event role anchors.
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == instance["id"],
            delivery_graph_requests.c.kind.in_([revision.CHECK,revision.CHECK+"_seal"])))
    retry=data[2].post(path+"/checks",json=dict(request_key=body["request_key"],
        expected_preview_fingerprint=value["preview_fingerprint"],consent=revision.CHECK_CONSENT))
    assert retry.status_code == 409,retry.text
    assert "submission_rejection" not in retry.json().get("error",{}),retry.text
    assert data[2].post(f"/api/internal/instances/{check_iid}/runs",json=dict(expected_revision=1,
        expected_release_fingerprint=base["fingerprint"],input={"column":"quantity"},request_key="pollute-again")).status_code == 409
    assert data[2].get(f"/api/internal/instances/{check_iid}/runs/{accepted['run_id']}").status_code == 409
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.project_id==data[5],grants.c.resource_id==data[6]).values(revoked=True))
    # The original stop controller uses only owned metadata after revocation.
    event.listen(data[0].engine,"before_cursor_execute",observe)
    try:
        stopped=data[2].post(f"/api/internal/instances/{check_iid}/runs/{accepted['run_id']}/commands",json=dict(command="cancel",version=1))
        assert stopped.status_code == 200,stopped.text
    finally:
        event.remove(data[0].engine,"before_cursor_execute",observe)
    assert private == [],private


def test_revoked_new_goal_material_gate_precedes_private_goal_and_proposal_reads(env):
    data,aid,base,instance,path,body,value,updated = ready(env)
    private=[]
    def observed(conn,cursor,statement,parameters,context,executemany):
        if re.search(r"(?:^SELECT |, )(?:goal_card_versions|delivery_graph_requests|internal_releases)\.snapshot(?:,|\s+\nFROM)",statement):
            private.append(statement)
    event.listen(data[0].engine,"before_cursor_execute",observed)
    try:
        assert data[2].get(path+"/previews/"+body["request_key"]).status_code == 200
        assert private,"positive SQL control must identify private Goal/proposal reads"
        private.clear()
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.project_id == data[5],grants.c.resource_id == data[6]).values(revoked=True))
        assert data[2].get(path+"/context").status_code == 403
        assert data[2].get(path+"/previews/"+body["request_key"]).status_code == 403
        assert data[2].post(path+"/previews",json=body).status_code == 403
    finally:
        event.remove(data[0].engine,"before_cursor_execute",observed)
    assert private == [],private


@pytest.mark.parametrize("case",["deliver","lost","navigation","rejected"])
def test_visible_same_goal_revision_check_release_adopt_and_new_run(env,tmp_path,case):
    import os
    import subprocess
    import threading
    from pathlib import Path

    data,aid,base,instance,cid,content,app = baseline(env)
    old = jobs.enqueue(data[0],data[3],instance["id"],instance["revision"],base["fingerprint"],
        {"column":"amount"},"before-browser-goal-edit",limits(data),csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    drive(data,old["run_id"])
    other = data[2].post("/api/projects",json={"name":"Other owned project"}).json()["id"]
    instance2 = create(data,base)
    data[0].project(data[4],"Other account project")
    with data[0].tx() as c:
        counts = {t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
    info = dict(case=case,project=data[5],other=other,app=aid,instance=instance["id"],instance2=instance2["id"],card=cid,
        output=str(tmp_path/"page-result.json"))
    (tmp_path/"info.json").write_text(json.dumps(info))
    process=None
    watchdog=None
    try:
        with (tmp_path/"node.stderr").open("w") as errors:
            process=subprocess.Popen(["node","tests/csv_goal_revision.cjs",str(tmp_path/"info.json")],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,
                env={**os.environ,"NODE_PATH":str(Path.cwd()/"scripts/engineering-ci/node_modules")})
            watchdog=threading.Timer(150,process.kill)
            watchdog.start()
            for line in process.stdout:
                request=json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    drive(data,request["run"])
                    answer=dict(status=200,text="{}")
                elif request.get("command") == "drift":
                    changed=jobs.enqueue(data[0],data[3],instance["id"],instance["revision"],base["fingerprint"],
                        {"column":"amount"},"explicit-intervening-run",limits(data))
                    drive(data,changed["run_id"])
                    answer=dict(status=200,text="{}")
                elif request.get("command") == "proof":
                    current=jobs.inspect_job(data[0],data[3],request["run"])
                    assert current["result"]["sum"] == "5" and current["instance_id"] == instance["id"]
                    before=jobs.inspect_job(data[0],data[3],old["run_id"])
                    assert before["result"]["sum"] == "30" and before["release_id"] == base["id"]
                    with data[0].tx() as c:
                        frozen=c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==request["run"])).scalar_one()
                        original=c.execute(select(app_drafts).where(app_drafts.c.id==aid)).mappings().one()
                        actual_counts={t.name:c.execute(select(func.count()).select_from(t)).scalar() for t in (grants,principals)}
                    assert actual_counts==counts and original["candidate"]==base["snapshot"]["draft"]["candidate"]
                    assert frozen["goal"]["goal"] == "明确汇总 quantity，保留原材料与历史"
                    assert frozen["runtime_id"] == instance["runtime_id"]
                    (tmp_path/"actual-browser-delivery.json").write_text(json.dumps(dict(
                        old=before,new=current,contract=frozen,unchanged_counts=counts),ensure_ascii=False,indent=2))
                    answer=dict(status=200,text="{}")
                else:
                    response=data[2].request(request["method"],request["path"],json=request.get("body"),headers=request.get("headers"))
                    answer=dict(status=response.status_code,text=response.text,content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps(dict(id=request["id"],**answer))+"\n")
                process.stdin.flush()
            process.stdin.close()
            code=process.wait(timeout=15)
        assert code == 0,(tmp_path/"node.stderr").read_text()
        page=json.loads((tmp_path/"page-result.json").read_text())
        assert page["status"] == "PASS",page
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
