"""Real HTTP/current-authority/persistent DeliveryGraph planning, no business send."""

import copy
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_internal_lifecycle import limits, setup_draft

from sim2act.api import create_app
from sim2act.db import Store, app_drafts, fingerprint, grants, meta, resources
from sim2act.db import delivery_graph_anchors as anchors
from sim2act.db import delivery_graph_requests as requests
from sim2act.db import delivery_graph_scope_jobs as jobs
from sim2act.db import delivery_graph_source_versions as versions
from sim2act.db import delivery_graph_states as states


def path(env, aid):
    return f"/api/projects/{env[5]}/apps/{aid}/delivery-graph"


def snapshot(env):
    with env[0].tx() as c:
        return {
            t.name: sorted([dict(r) for r in c.execute(select(t)).mappings()], key=fingerprint)
            for t in meta.sorted_tables
        }


def setup_graph(env):
    aid, fp = setup_draft(env)
    reply = env[2].post(
        path(env, aid) + "/derive",
        json=dict(expected_candidate_fingerprint=fp, request_key="derive"),
    )
    assert reply.status_code == 201, reply.text
    return aid, fp, reply.json()


def change(graph, key="change"):
    node = next(n for n in graph["graph"]["nodes"] if n["kind"] == "SOURCE")
    return dict(
        expected_graph_fingerprint=graph["graph_fingerprint"],
        request_key=key,
        changes=[
            dict(
                node_id=node["id"],
                expected_revision=node["revision"],
                expected_content_fingerprint=node["content_fingerprint"],
            )
        ],
    )


def test_csv_real_anchor_restart_idempotency_and_pending_scope_jobs(env):
    aid, fp = setup_draft(env)
    before = snapshot(env)
    empty = env[2].get(path(env, aid))
    assert empty.status_code == 409 and "has not been derived" in empty.text
    assert snapshot(env) == before
    body = dict(expected_candidate_fingerprint=fp, request_key="derive")
    made = env[2].post(path(env, aid) + "/derive", json=body)
    assert made.status_code == 201, made.text
    graph = made.json()
    assert graph["namespace"] == "delivery-graph-apps.v1" and graph["state"] == "PLANNING_ONLY"
    assert graph["owner_acceptance"] == "PENDING" and graph["semantic_status"] == "UNKNOWN"
    assert env[2].get(path(env, aid)).json()["graph_fingerprint"] == graph["graph_fingerprint"]
    frozen = snapshot(env)
    fresh_store = Store(env[1].database_url, test_only=True)
    # Same actual database/schema; this fixture's SQLite restart is independent Store.
    if not env[0].sqlite:
        fresh_store.engine.dispose()
        fresh_store = env[0]
    fresh = TestClient(create_app(fresh_store, env[1]))
    fresh.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        assert fresh.post(path(env, aid) + "/derive", json=body).json()["cached"]
        assert snapshot(env) == frozen
        accepted = fresh.post(path(env, aid) + "/plans", json=change(graph))
        assert accepted.status_code == 201, accepted.text
        answer = accepted.json()
        assert answer["receipt"]["patch_executed"] is False
        assert answer["receipt"]["revalidation_scope"] == "APP"
        assert [j["app_id"] for j in answer["scope_jobs"]] == [aid]
        assert answer["scope_jobs"][0]["status"] == "PENDING"
        after = snapshot(env)
        retry = fresh.post(path(env, aid) + "/plans", json=change(graph))
        assert retry.status_code == 201 and retry.json()["cached"]
        assert snapshot(env) == after
        assert len(fresh.get(path(env, aid) + "/plans").json()["items"]) == 1
        for table in before:
            if not table.startswith("delivery_graph_"):
                assert before[table] == after[table], table
    finally:
        fresh.close()
        if fresh_store is not env[0]:
            fresh_store.engine.dispose()


@pytest.mark.parametrize(
    "extra", ["context", "graph", "previous_receipt", "authorized", "scope", "presentation_only"]
)
def test_client_fields_never_gain_context_or_write(env, extra):
    aid, _, graph = setup_graph(env)
    before = snapshot(env)
    response = env[2].post(path(env, aid) + "/plans", json={**change(graph), extra: {}})
    assert response.status_code == 422
    assert snapshot(env) == before


@pytest.mark.parametrize(
    "attack",
    [
        "scope",
        "identity",
        "candidate",
        "resource_hash",
        "resource_content",
        "resource_status",
        "runtime_revoke",
        "stale_node",
        "same_key",
    ],
)
def test_scope_source_and_version_rejections_write_nothing(env, attack):
    aid, _, graph = setup_graph(env)
    body = change(graph)
    url = path(env, aid) + "/plans"
    if attack == "scope":
        other = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
        url = f"/api/projects/{other}/apps/{aid}/delivery-graph/plans"
    elif attack == "identity":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif attack == "candidate":
        with env[0].tx() as c:
            c.execute(update(app_drafts).where(app_drafts.c.id == aid).values(fingerprint="0" * 64))
    elif attack.startswith("resource_"):
        values = (
            {"hash": "0" * 64}
            if attack == "resource_hash"
            else ({"content": "changed"} if attack == "resource_content" else {"format": "retired"})
        )
        with env[0].tx() as c:
            c.execute(update(resources).where(resources.c.id == env[6]).values(**values))
    elif attack == "runtime_revoke":
        with env[0].tx() as c:
            runtime = c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
            ).scalar_one()
            c.execute(update(grants).where(grants.c.principal_id == runtime).values(revoked=True))
    elif attack == "stale_node":
        body["changes"][0]["expected_revision"] += 1
    elif attack == "same_key":
        assert env[2].post(url, json=body).status_code == 201
        body["changes"] = [
            dict(
                node_id=n["id"],
                expected_revision=n["revision"],
                expected_content_fingerprint=n["content_fingerprint"],
            )
            for n in graph["graph"]["nodes"]
            if n["kind"] == "VIEW"
        ]
    before = snapshot(env)
    result = env[2].post(url, json=body)
    assert result.status_code >= 400, result.text
    assert snapshot(env) == before


@pytest.mark.parametrize(
    "attack", ["state_rehash", "seal_rehash", "source_bool", "receipt_bool", "receipt_int", "job"]
)
def test_persistent_coherent_tampering_is_typed_and_zero_write(env, attack):
    aid, _, graph = setup_graph(env)
    body = change(graph)
    answer = env[2].post(path(env, aid) + "/plans", json=body)
    assert answer.status_code == 201, answer.text
    with env[0].tx() as c:
        table = (
            states
            if attack in {"state_rehash", "seal_rehash"}
            else versions
            if attack == "source_bool"
            else jobs
            if attack == "job"
            else requests
        )
        query = select(table).where(table.c.app_id == aid)
        if table is requests:
            query = query.where(table.c.kind == "plan")
        row = c.execute(query).mappings().first()
        value = copy.deepcopy(row["snapshot"])
        if attack in {"state_rehash", "seal_rehash"}:
            value["graph_revision"] = True
        elif attack == "source_bool":
            value["revision"] = True
        elif attack == "job":
            value["status"] = "PASS"
        else:
            value["response"]["receipt"]["patch_executed"] = 0 if attack == "receipt_bool" else True
        c.execute(
            update(table)
            .where(*(table.c[k.name] == row[k.name] for k in table.primary_key))
            .values(snapshot=value, fingerprint=fingerprint(value))
        )
        if attack == "seal_rehash":
            c.execute(
                update(anchors)
                .where(anchors.c.id == row["anchor_id"])
                .values(snapshot=value, fingerprint=fingerprint(value))
            )
    before = snapshot(env)
    response = env[2].post(path(env, aid) + "/plans", json=body)
    assert response.status_code >= 400, response.text
    assert snapshot(env) == before
    history_reply = env[2].get(path(env, aid) + "/plans")
    assert history_reply.status_code >= 400, history_reply.text
    assert snapshot(env) == before


def test_pg_existing_crud_role_graph_and_plan_never_ddl(env, runtime_role):
    from sqlalchemy import event
    from test_registered_run_generation_pg_role import role_capabilities, schema_objects

    aid, fp = setup_draft(env)
    role = Store(runtime_role, test_only=True)
    settings = replace(env[1], database_url=runtime_role)
    client = TestClient(create_app(role, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    verbs = []

    def inspect_sql(_conn, _cursor, sql, _params, _ctx, _many):
        verb = sql.lstrip().split(None, 1)[0].upper()
        verbs.append(verb)
        assert verb not in {"CREATE", "ALTER", "DROP", "GRANT", "REVOKE", "TRUNCATE"}

    event.listen(role.engine, "before_cursor_execute", inspect_sql)
    try:
        assert role_capabilities(role) == dict(
            rolsuper=False, rolcreatedb=False, rolcreaterole=False, schema_create=False
        )
        inventory = schema_objects(role)
        response = client.post(
            path(env, aid) + "/derive",
            json=dict(expected_candidate_fingerprint=fp, request_key="role"),
        )
        assert response.status_code == 201, response.text
        result = client.post(path(env, aid) + "/plans", json=change(response.json()))
        assert result.status_code == 201, result.text
        assert client.get(path(env, aid) + "/plans").status_code == 200
        assert schema_objects(role) == inventory and "INSERT" in verbs
    finally:
        client.close()
        role.engine.dispose()


def test_server_registry_version_sequence_stable_slots_and_authorization_generation(
    env, monkeypatch
):
    from pathlib import Path

    aid, fp, graph = setup_graph(env)
    old_ids = {n["key"]: n["id"] for n in graph["graph"]["nodes"]}
    original = Path.read_bytes

    def revised(path):
        value = original(path)
        return (
            value + b"\n# synthetic trusted registry revision\n"
            if path.name == "preflight.py"
            else value
        )

    monkeypatch.setattr(Path, "read_bytes", revised)
    before = snapshot(env)
    assert env[2].get(path(env, aid)).status_code == 409
    assert (
        env[2]
        .post(
            path(env, aid) + "/derive",
            json=dict(expected_candidate_fingerprint=fp, request_key="derive"),
        )
        .status_code
        == 409
    )
    assert snapshot(env) == before
    changed = env[2].post(
        path(env, aid) + "/derive",
        json=dict(expected_candidate_fingerprint=fp, request_key="registry2"),
    )
    assert changed.status_code == 201, changed.text
    new = changed.json()
    assert new["graph_revision"] == 2 and new["authorization_revision"] == 1
    assert {n["key"]: n["id"] for n in new["graph"]["nodes"]} == old_ids
    assert all(
        v["revision"] == (1 if k.startswith(("source:", "goal:")) else 2)
        for k, v in new["source_versions"].items()
    )
    with env[0].tx() as c:
        row = c.execute(select(grants).where(grants.c.principal_id == env[3])).mappings().first()
        c.execute(
            update(grants)
            .where(grants.c.id == row["id"])
            .values(expires_at=row["expires_at"] + 1000)
        )
    before = snapshot(env)
    assert env[2].get(path(env, aid)).status_code == 403
    assert snapshot(env) == before
    next_reply = env[2].post(
        path(env, aid) + "/derive",
        json=dict(expected_candidate_fingerprint=fp, request_key="auth2"),
    )
    assert next_reply.status_code == 201, next_reply.text
    assert next_reply.json()["authorization_revision"] == 2
    assert next_reply.json()["source_versions"] == new["source_versions"]


def test_real_report_origin_two_sources_project_pending_jobs_and_unsupported_omission(
    env, tmp_path
):
    from test_conditional_run_bindings import env as bounded_env
    from test_report_manifest_apps import promoted

    bounded = bounded_env.__wrapped__(env)
    app, parent, _, _, wires = promoted(bounded, tmp_path)
    peer, peer_fp = setup_draft(env)
    peer_reply = env[2].post(
        path(env, peer) + "/derive",
        json=dict(expected_candidate_fingerprint=peer_fp, request_key="peer"),
    )
    assert peer_reply.status_code == 201, peer_reply.text
    before = snapshot(env)
    url = path(env, app["id"])
    reply = env[2].post(
        url + "/derive",
        json=dict(expected_candidate_fingerprint=app["fingerprint"], request_key="report"),
    )
    assert reply.status_code == 201, reply.text
    graph = reply.json()
    proof = app["candidate"]["report_proof"]
    assert set(graph["graph"]["resource_ids"]) == {
        proof["source_resource_id"],
        proof["target_resource_id"],
    }
    assert not [e for e in graph["graph"]["edges"] if e["provenance"] == "ACTUAL_READ"]
    result = env[2].post(url + "/plans", json=change(graph))
    assert result.status_code == 201, result.text
    value = result.json()
    assert value["receipt"]["revalidation_scope"] == "PROJECT"
    assert {j["app_id"] for j in value["scope_jobs"]} == {app["id"], peer}
    assert all(j["status"] == "PENDING" for j in value["scope_jobs"])
    assert value["scope_expansion"]["status"] == "BLOCKED_PARTIAL"
    assert parent["id"] in {v["app_id"] for v in value["scope_expansion"]["omissions"]}
    after = snapshot(env)
    assert all(before[k] == after[k] for k in before if not k.startswith("delivery_graph_"))
    assert len(wires) == 3  # source two, extraction one; graph/plan make no provider requests.


def test_competing_same_key_serializes_one_anchor_and_one_pending_job(env):
    from concurrent.futures import ThreadPoolExecutor

    aid, fp = setup_draft(env)

    def submit(_):
        return env[2].post(
            path(env, aid) + "/derive",
            json=dict(expected_candidate_fingerprint=fp, request_key="race"),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(submit, range(2)))
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert len({r.json()["graph_fingerprint"] for r in replies}) == 1
    assert sorted(r.json()["cached"] for r in replies) == [False, True]
    graph = replies[0].json()

    def changed(_):
        return env[2].post(path(env, aid) + "/plans", json=change(graph, "race-plan"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        plans = list(pool.map(changed, range(2)))
    assert all(r.status_code == 201 for r in plans), [r.text for r in plans]
    assert len({r.json()["scope_jobs"][0]["id"] for r in plans}) == 1
    with env[0].tx() as c:
        assert len(c.execute(select(anchors).where(anchors.c.app_id == aid)).all()) == 1
        assert len(c.execute(select(jobs).where(jobs.c.source_app_id == aid)).all()) == 1


def report_project(env, tmp_path):
    from test_conditional_run_bindings import env as bounded_env
    from test_report_manifest_apps import promoted

    bounded = bounded_env.__wrapped__(env)
    app, *_ = promoted(bounded, tmp_path)
    peer, peer_fp, peer_graph = setup_graph(env)
    made = env[2].post(
        path(env, app["id"]) + "/derive",
        json=dict(expected_candidate_fingerprint=app["fingerprint"], request_key="report"),
    )
    assert made.status_code == 201, made.text
    return app, peer, peer_fp, peer_graph, made.json()


def lock_node(env, aid, graph, key="lock"):
    from sim2act.delivery_graph_apps import set_lock

    body = change(graph)
    value = dict(
        expected_graph_fingerprint=graph["graph_fingerprint"],
        request_key=key,
        change=body["changes"][0],
        locked=True,
    )
    return set_lock(env[0], env[3], env[5], aid, value, limits(env))


@pytest.mark.parametrize(
    "attack", ["peer_anchor", "peer_auth", "peer_lock", "membership", "peer_graph_bool"]
)
def test_project_replay_and_history_bind_current_peer_graph_authority_lock_membership(
    env, tmp_path, attack
):
    app, peer, peer_fp, peer_graph, graph = report_project(env, tmp_path)
    body = change(graph)
    accepted = env[2].post(path(env, app["id"]) + "/plans", json=body)
    assert accepted.status_code == 201, accepted.text
    value = accepted.json()
    binding = next(v for v in value["scope_expansion"]["applications"] if v["app_id"] == peer)
    assert binding["graph_fingerprint"] == peer_graph["graph_fingerprint"]
    if attack == "peer_anchor":
        with env[0].tx() as c:
            c.execute(update(anchors).where(anchors.c.app_id == peer).values(fingerprint="0" * 64))
    elif attack == "peer_auth":
        with env[0].tx() as c:
            runtime = c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == peer)
            ).scalar_one()
            row = (
                c.execute(select(grants).where(grants.c.principal_id == runtime)).mappings().first()
            )
            c.execute(
                update(grants)
                .where(grants.c.id == row["id"])
                .values(expires_at=row["expires_at"] + 1000)
            )
    elif attack == "peer_lock":
        lock_node(env, peer, peer_graph)
        response = env[2].post(
            path(env, peer) + "/derive",
            json=dict(expected_candidate_fingerprint=peer_fp, request_key="locked"),
        )
        assert response.status_code == 201, response.text
    elif attack == "membership":
        setup_draft(env)
    else:
        with env[0].tx() as c:
            row = c.execute(select(states).where(states.c.app_id == peer)).mappings().one()
            data = copy.deepcopy(row["snapshot"])
            data["graph_revision"] = True
            c.execute(
                update(states)
                .where(states.c.app_id == peer)
                .values(snapshot=data, fingerprint=fingerprint(data))
            )
            c.execute(
                update(anchors)
                .where(anchors.c.id == row["anchor_id"])
                .values(snapshot=data, fingerprint=fingerprint(data))
            )
    before = snapshot(env)
    retry = env[2].post(path(env, app["id"]) + "/plans", json=body)
    assert retry.status_code >= 400, retry.text
    assert env[2].get(path(env, app["id"]) + "/plans").status_code >= 400
    assert snapshot(env) == before
    fresh = env[2].post(
        path(env, app["id"]) + "/plans", json=change(graph, "fresh-after-peer-change")
    )
    if fresh.status_code < 400:
        result = fresh.json()
        assert result["scope_expansion"]["status"] == "BLOCKED_PARTIAL", fresh.text
        if attack != "membership":
            assert peer not in {job["app_id"] for job in result["scope_jobs"]}
    else:
        assert snapshot(env) == before


@pytest.mark.parametrize("which", ["target", "peer"])
def test_initial_affected_manual_lock_rejects_project_without_ledger_writes(env, tmp_path, which):
    app, peer, peer_fp, peer_graph, graph = report_project(env, tmp_path)
    aid, g, fp = (
        (app["id"], graph, app["fingerprint"]) if which == "target" else (peer, peer_graph, peer_fp)
    )
    lock_node(env, aid, g)
    made = env[2].post(
        path(env, aid) + "/derive",
        json=dict(expected_candidate_fingerprint=fp, request_key="lock-anchor"),
    )
    assert made.status_code == 201, made.text
    if which == "target":
        graph = made.json()
    before = snapshot(env)
    response = env[2].post(path(env, app["id"]) + "/plans", json=change(graph))
    assert (
        response.status_code in {400, 409} and response.json()["error"]["code"] == "LOCK_CONFLICT"
    ), response.text
    assert snapshot(env) == before


def test_internal_lock_owner_and_client_context_are_not_authority(env):
    from sim2act.delivery_graph_apps import set_lock
    from sim2act.errors import DomainError

    aid, _, graph = setup_graph(env)
    value = dict(
        expected_graph_fingerprint=graph["graph_fingerprint"],
        request_key="bad-owner",
        change=change(graph)["changes"][0],
        locked=True,
    )
    before = snapshot(env)
    with pytest.raises(DomainError) as error:
        set_lock(env[0], env[4], env[5], aid, value, limits(env))
    assert error.value.code == "PERMISSION_DENIED"
    assert snapshot(env) == before


def test_project_missing_peer_anchor_is_explicit_partial_not_candidate_only_job(env, tmp_path):
    app, peer, _, _, graph = report_project(env, tmp_path)
    extra, _ = setup_draft(env)
    before = snapshot(env)
    reply = env[2].post(path(env, app["id"]) + "/plans", json=change(graph, "partial"))
    assert reply.status_code == 201, reply.text
    value = reply.json()
    assert value["scope_expansion"]["status"] == "BLOCKED_PARTIAL"
    assert {"app_id": extra, "reason": "GRAPH_NOT_DERIVED"} in value["scope_expansion"]["omissions"]
    assert extra not in {v["app_id"] for v in value["scope_jobs"]}
    assert {v["app_id"] for v in value["expansion"]["applications"]} == {app["id"], peer}
    assert value["outer_fingerprint"] == fingerprint(
        {"core": value["receipt"], "expansion": value["expansion"]}
    )
    assert value["native_outer_fingerprint"] == fingerprint(
        {k: v for k, v in value.items() if k not in {"native_outer_fingerprint", "cached"}}
    )
    after = snapshot(env)
    assert all(before[k] == after[k] for k in before if not k.startswith("delivery_graph_"))
