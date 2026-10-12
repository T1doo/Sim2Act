"""Independent literal logic: actual SQLite, cold API and ordinary NoModel Worker."""

import copy
import json
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, insert, select, update
from test_goal_text_applications import CONTENT, release_instance, run_input
from test_registered_text_extraction import prepared, snapshot

from sim2act import text_logic_reuse as logic
from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    goal_application_candidates,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    new_id,
    principals,
    resources,
    runs,
)
from sim2act.worker import Worker


def mint(data, url, key="authorize-independent-text"):
    preview = data[2].get(url + "/text-logic-options")
    assert preview.status_code == 200, preview.text
    p = preview.json()
    body = dict(expected_proof_fingerprint=p["source_proof_fingerprint"],
                expected_release_fingerprint=p["release_fingerprint"],
                consent="AUTHORIZE_DATA_FREE_TEXT_LOGIC_IN_THIS_PROJECT", request_key=key)
    made = data[2].post(url + "/text-logic-authorizations", json=body)
    assert made.status_code == 201, made.text
    return made.json()["logic"], body


def binding(data, obj, target, key="bind-new-text"):
    response = data[2].get(f"/api/internal/text-logics/{obj['id']}/materials")
    assert response.status_code == 200, response.text
    t = next(t for t in response.json()["items"] if t["target_app_id"] == target)
    return dict(expected_logic_fingerprint=obj["fingerprint"], target_app_id=target,
                expected_target_draft_fingerprint=t["candidate_fingerprint"],
                expected_resource_id=t["resource_id"], expected_source_hash=t["source_hash"],
                name="New material literal app", consent="CREATE_NEW_READ_ONLY_RUNTIME_FOR_THIS_TEXT_RESOURCE",
                request_key=key)


def bind(data, obj, body):
    response = data[2].post(f"/api/internal/text-logics/{obj['id']}/bindings", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def revoke_source(data, *, delete_content=True):
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
        if delete_content:
            c.execute(delete(resources).where(resources.c.id == data[5]))


def revoke_logic(data, obj):
    body = dict(expected_logic_fingerprint=obj["fingerprint"], consent="REVOKE_DATA_FREE_TEXT_LOGIC",
                request_key="revoke-independent-text")
    response = data[2].post(f"/api/internal/text-logics/{obj['id']}/revoke", json=body)
    assert response.status_code == 200, response.text
    return body


def source_barrier(data, aid, release, instance, run):
    from sql_private_barrier import PrivateReadBarrier

    with data[0].tx() as c:
        generation = c.execute(select(goal_application_candidates.c.run_id).where(
            goal_application_candidates.c.app_id == aid)).scalar_one()
        approval_id = c.execute(select(internal_releases.c.approval_id).where(
            internal_releases.c.id == release["id"])).scalar_one()
    barrier = PrivateReadBarrier(data[0], {run["id"], generation}, {data[5]})
    barrier.rules.update({
        "app_drafts": (app_drafts, "id", {aid}, {"candidate"}),
        "internal_releases": (internal_releases, "id", {release["id"]}, {"snapshot"}),
        "internal_approvals": (internal_approvals, "id", {approval_id}, {"payload"}),
        "internal_run_bindings": (internal_run_bindings, "run_id", {run["id"]}, {"snapshot"}),
        "internal_app_runs": (internal_app_runs, "instance_id", {instance["id"]}, {"input", "output", "error"}),
        "internal_instances": (internal_instances, "id", {instance["id"]}, {"history"}),
        "internal_instance_data": (internal_instance_data, "instance_id", {instance["id"]}, {"data"}),
    })
    return barrier


@pytest.mark.parametrize("format", ["txt", "md"])
def test_authorize_retire_source_cold_bind_and_worker_no_private_reads(env, format):
    data, aid, oldrel, oldinst, oldrun, target, rid, url = prepared(env, format)
    obj, auth = mint(data, url)
    body = binding(data, obj, target)
    revoke_source(data)
    assert data[2].get("/api/apps/" + aid).status_code in {403, 409}
    assert data[2].get("/api/internal/releases/" + oldrel["id"]).status_code in {403, 409}
    before = snapshot(data[0])
    cold = Store(data[1].database_url, test_only=True)
    barrier = source_barrier(data, aid, oldrel, oldinst, oldrun)
    barrier.attach(cold)
    try:
        with barrier, TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            cold_data = (cold, data[1], client, *data[3:])
            index = client.get(f"/api/projects/{data[4]}/text-logics")
            assert index.status_code == 200, index.text
            assert index.json()["items"][0]["id"] == obj["id"]
            # Prove the barrier rejects an actual old private-cell evaluation.
            from sqlalchemy.exc import DatabaseError

            # Deleted resources have no cell; use the retained source draft.
            with pytest.raises(DatabaseError), cold.tx() as c:
                c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            assert barrier.blocked
            barrier.blocked.clear()
            cached = client.post(url + "/text-logic-authorizations", json=auth)
            assert cached.status_code == 201 and cached.json()["cached"] is True
            assert client.get(f"/api/internal/text-logics/{obj['id']}/materials").status_code == 200
            made = bind(cold_data, obj, body)
            got = client.get(f"/api/internal/text-logics/{obj['id']}/bindings",
                             params={"request_key": body["request_key"]})
            assert got.status_code == 200 and got.json()["id"] == made["id"]
            assert bind(cold_data, obj, body)["id"] == made["id"]
            draft = client.get("/api/apps/" + made["id"]).json()
            candidate = draft["candidate"]
            assert candidate["manifest"]["source_run_ref"] == obj["id"]
            assert candidate["manifest"]["data_bindings"] == [{"binding_id": "source", "resource_ref": rid}]
            serialized = json.dumps([obj, candidate], ensure_ascii=False)
            assert CONTENT not in serialized and data[5] not in serialized
            assert data[6]["content"]["goal"] not in serialized
            release, instance = release_instance(cold_data, made["id"])
            result = run_input(cold_data, release, instance, {"term": "Gamma"}, "unseen-new-term")
            assert result["status"] == "SUCCEEDED", result
            app_run = client.get(f"/api/internal/instances/{instance['id']}/runs/{result['id']}").json()
            output = app_run["result"]
            assert output["citations"] == [dict(start_line=2, end_line=2, quote="Gamma new obligation"),
                                            dict(start_line=4, end_line=4, quote="Gamma final note")]
            assert output["semantic_status"] == "UNKNOWN"
            invalid = run_input(cold_data, release, instance, {"term": " padded "}, "invalid-term")
            assert invalid["status"] == "FAILED"
            with cold.tx() as c:
                gs = c.execute(select(grants).where(grants.c.principal_id == made["runtime_id"])).mappings().all()
                assert len(gs) == 1 and gs[0]["resource_id"] == rid and gs[0]["tool_ref"] == "resource.read"
                assert c.execute(select(principals.c.token_hash).where(
                    principals.c.id == made["runtime_id"])).scalar_one() is None
                records = c.execute(select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == instance["id"])).mappings().all()
                assert len(records) == 1 and records[0]["data"]["result"] == output
            assert not barrier.blocked
        after = snapshot(data[0])
        for table, rows in before.items():
            assert all(row in after[table] for row in rows), table
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize("field,value", [
    ("expected_logic_fingerprint", "0" * 64),
    ("expected_target_draft_fingerprint", "0" * 64),
    ("expected_resource_id", "res_" + "0" * 32),
    ("expected_source_hash", "0" * 64),
])
def test_exact_target_request_conflict_has_no_partial_rows(env, field, value):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    body = binding(data, obj, target)
    before = snapshot(data[0])
    reply = data[2].post(f"/api/internal/text-logics/{obj['id']}/bindings", json={**body, field: value})
    assert reply.status_code == 409, reply.text
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("mutation", ["missing_auth_seal", "changed_marker", "missing_marker", "expanded_runtime", "token_runtime"])
def test_independent_markers_seals_and_fresh_identity_fail_closed(env, mutation):
    data, _, _, _, _, target, rid, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    with data[0].tx() as c:
        if mutation == "missing_auth_seal":
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == obj["id"],
                delivery_graph_requests.c.kind == logic.AUTH + "_seal"))
        elif mutation == "expanded_runtime":
            c.execute(insert(grants).values(id=new_id("grant"), principal_id=made["runtime_id"],
                project_id=data[4], resource_id=rid, tool_ref="resource.read", expires_at=time.time() + 100, revision=1, revoked=False))
        elif mutation == "token_runtime":
            c.execute(update(principals).where(principals.c.id == made["runtime_id"]).values(token_hash="invalid-new-token"))
        else:
            row = c.execute(select(app_drafts).where(app_drafts.c.id == made["id"])).mappings().one()
            value = copy.deepcopy(row["candidate"])
            if mutation == "missing_marker":
                value.pop("task_proof")
                value["manifest"].update(origin="goal", source_run_ref=None)
            else:
                value["task_proof"]["proof"]["kind"] = "completed_registered_text_apprun.v1"
            c.execute(update(app_drafts).where(app_drafts.c.id == made["id"]).values(candidate=value, fingerprint=fingerprint(value)))
    assert data[2].get("/api/apps/" + made["id"]).status_code == 409


def test_revoke_independent_source_gone_irreversible_and_history(env):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    revoke_source(data)
    body = revoke_logic(data, obj)
    assert data[2].post(f"/api/internal/text-logics/{obj['id']}/revoke", json=body).status_code == 200
    with data[0].tx() as c:
        c.execute(update(internal_approvals).where(internal_approvals.c.id == obj["id"]).values(consumed=False))
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == obj["id"],
            delivery_graph_requests.c.kind == logic.REVOKE))
    assert data[2].get("/api/apps/" + made["id"]).status_code == 403
    index = data[2].get(f"/api/projects/{data[4]}/text-logics")
    assert index.status_code == 200 and index.json()["items"][0]["status"] == "REVOKED"


@pytest.mark.parametrize("revoked", ["logic", "target", "runtime"])
def test_revocation_after_enqueue_cannot_append(env, revoked):
    data, _, _, _, _, target, rid, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    release, instance = release_instance(data, made["id"])
    queued = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        input={"term": "Gamma"}, request_key="enqueue-before-revocation"))
    assert queued.status_code == 202, queued.text
    if revoked == "logic":
        revoke_logic(data, obj)
    else:
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == rid,
                grants.c.principal_id == (data[3] if revoked == "target" else made["runtime_id"])).values(revoked=True))
    assert Worker(data[0], data[1]).once()
    # Current content GET correctly refuses after revocation; inspect durable metadata.
    assert data[2].get("/api/runs/" + queued.json()["run_id"]).status_code in {403, 409}
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == queued.json()["run_id"])).scalar_one() == "WAITING_RESOURCE"
        assert c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == instance["id"])).first() is None


def test_binding_transaction_rolls_back_and_key_conflicts(env):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    body = binding(data, obj, target)
    before = snapshot(data[0])

    def fail(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO task_extractions"):
            raise RuntimeError("synthetic binding transaction fault")

    event.listen(data[0].engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="synthetic binding"):
            bind(data, obj, body)
    finally:
        event.remove(data[0].engine, "before_cursor_execute", fail)
    assert snapshot(data[0]) == before
    made = bind(data, obj, body)
    assert data[2].post(f"/api/internal/text-logics/{obj['id']}/bindings", json={**body, "name": "different"}).status_code == 409
    assert data[2].get(f"/api/internal/text-logics/{obj['id']}/bindings", params={"request_key": body["request_key"]}).json()["id"] == made["id"]


def test_cross_identity_budget_and_expiry(env, monkeypatch):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    body = binding(data, obj, target)
    before = snapshot(data[0])
    data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    for path in (f"/api/internal/text-logics/{obj['id']}", f"/api/internal/text-logics/{obj['id']}/materials",
                 f"/api/projects/{data[4]}/text-logics", url + "/text-logic-options"):
        assert data[2].get(path).status_code == 403
    data[2].headers["Authorization"] = "Bearer synthetic-test-A"
    with TestClient(create_app(data[0], replace(data[1], run_seconds=1))) as tight:
        tight.headers["Authorization"] = "Bearer synthetic-test-A"
        reply = tight.post(f"/api/internal/text-logics/{obj['id']}/bindings", json=body)
        assert reply.status_code == 400 and reply.json()["error"]["code"] == "BUDGET_EXHAUSTED"
    assert snapshot(data[0]) == before
    monkeypatch.setattr(logic.time, "time", lambda: obj["expires_at"] + 1)
    assert data[2].post(f"/api/internal/text-logics/{obj['id']}/bindings", json=body).status_code == 403
    assert data[2].get(f"/api/internal/text-logics/{obj['id']}").json()["status"] == "EXPIRED"


def test_expiry_during_typed_append_rolls_back_entire_result(env, monkeypatch):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    release, instance = release_instance(data, made["id"])
    queued = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        input={"term": "Gamma"}, request_key="append-expiry"))
    assert queued.status_code == 202
    expired = False
    actual_time = time.time
    monkeypatch.setattr(logic, "time", SimpleNamespace(time=lambda: obj["expires_at"] + 1 if expired else actual_time()))

    def after_append(conn, cursor, statement, parameters, context, many):
        nonlocal expired
        if statement.startswith("INSERT INTO internal_instance_data"):
            expired = True

    event.listen(data[0].engine, "after_cursor_execute", after_append)
    try:
        assert Worker(data[0], data[1]).once()
    finally:
        event.remove(data[0].engine, "after_cursor_execute", after_append)
    assert expired
    with data[0].tx() as c:
        assert c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == instance["id"])).first() is None
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id == instance["id"])).scalar_one() == 0
        assert c.execute(select(runs.c.status).where(runs.c.id == queued.json()["run_id"])).scalar_one() == "WAITING_RESOURCE"


@pytest.mark.parametrize("limit", ["logic", "binding"])
def test_capacity_counts_retained_authorities_and_bindings(env, monkeypatch, limit):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    if limit == "logic":
        revoke_logic(data, obj)
        monkeypatch.setattr(logic, "MAX_LOGICS", 1)
        preview = data[2].get(url + "/text-logic-options").json()
        body = dict(expected_proof_fingerprint=preview["source_proof_fingerprint"],
                    expected_release_fingerprint=preview["release_fingerprint"],
                    consent="AUTHORIZE_DATA_FREE_TEXT_LOGIC_IN_THIS_PROJECT", request_key="second-authority")
        path = url + "/text-logic-authorizations"
    else:
        body = binding(data, obj, target)
        bind(data, obj, body)
        monkeypatch.setattr(logic, "MAX_BINDINGS", 1)
        body = {**body, "request_key": "second-binding"}
        path = f"/api/internal/text-logics/{obj['id']}/bindings"
    before = snapshot(data[0])
    response = data[2].post(path, json=body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "BUDGET_EXHAUSTED", response.text
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("field,value", [("model_requests", False), ("formal_publication_enabled", 0), ("max_lines", 64.0)])
def test_single_resigned_authority_json_types_do_not_match_double_seals(env, field, value):
    data, _, _, _, _, _, _, url = prepared(env)
    obj, _ = mint(data, url)
    with data[0].tx() as c:
        row = c.execute(select(internal_approvals).where(internal_approvals.c.id == obj["id"])).mappings().one()
        changed = copy.deepcopy(row["payload"])
        if field == "max_lines":
            changed["recipe"][field] = value
        else:
            changed[field] = value
        c.execute(update(internal_approvals).where(internal_approvals.c.id == obj["id"]).values(
            payload=changed, fingerprint=fingerprint(changed)))
    assert data[2].get(f"/api/internal/text-logics/{obj['id']}").status_code == 409


@pytest.mark.parametrize("limit", ["logic", "binding"])
def test_actual64th_write_allowed_65th_denied_and_original_key_readable(env, limit):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, auth = mint(data, url)
    if limit == "logic":
        for i in range(1, 64):
            response = data[2].post(url + "/text-logic-authorizations", json={**auth, "request_key": f"authority-{i}"})
            assert response.status_code == 201, (i, response.text)
        body = {**auth, "request_key": "authority-65"}
        path = url + "/text-logic-authorizations"
        recovery = url + "/text-logic-receipts?request_key=" + auth["request_key"]
    else:
        original = binding(data, obj, target)
        for i in range(64):
            bind(data, obj, {**original, "request_key": f"binding-{i}"})
        body = {**original, "request_key": "binding-65"}
        path = f"/api/internal/text-logics/{obj['id']}/bindings"
        recovery = path + "?request_key=binding-0"
    before = snapshot(data[0])
    response = data[2].post(path, json=body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "BUDGET_EXHAUSTED"
    assert data[2].get(recovery).status_code == 200
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("kind", [logic.RELEASE_INDEX, logic.RELEASE_INDEX + "_seal"])
def test_release_index_either_seal_missing_refuses_new_history(env, kind):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    release, _ = release_instance(data, made["id"])
    revoke_source(data)
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made["id"],
            delivery_graph_requests.c.request_key == release["id"], delivery_graph_requests.c.kind == kind))
    assert data[2].get(f"/api/internal/apps/{made['id']}/releases").status_code == 409
    assert data[2].get(f"/api/internal/releases/{release['id']}").status_code == 409


def test_release_index_transaction_fault_rolls_back_approval_and_release(env):
    data, _, _, _, _, target, _, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    draft = data[2].get("/api/apps/" + made["id"]).json()
    preview = data[2].post(f"/api/internal/apps/{made['id']}/release-approvals", json=dict(
        expected_draft_fingerprint=draft["fingerprint"], sample_input={"term": "Gamma"}))
    assert preview.status_code == 201
    approval = preview.json()
    before = snapshot(data[0])

    def fail(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO delivery_graph_requests"):
            raise RuntimeError("synthetic release index write failure")

    event.listen(data[0].engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="synthetic release index"):
            data[2].post(f"/api/internal/approvals/{approval['id']}/commit", json={"fingerprint": approval["fingerprint"]})
    finally:
        event.remove(data[0].engine, "before_cursor_execute", fail)
    assert snapshot(data[0]) == before
    committed = data[2].post(f"/api/internal/approvals/{approval['id']}/commit", json={"fingerprint": approval["fingerprint"]})
    assert committed.status_code == 200, committed.text
    assert data[2].get(f"/api/internal/apps/{made['id']}/releases").json()["items"][0]["id"] == committed.json()["id"]
