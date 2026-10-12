"""SIMULATED owner choices on actual native GoalCard/API/Worker/ledger; LIVE0."""

import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select, update
from test_goal_text_applications import release_instance, run_input
from test_owner_acceptance import choice_body, prepare, state
from test_persistent_app_runs import NoModel
from test_registered_text_extraction import prepared, snapshot
from test_text_logic_reuse import bind, binding, mint, revoke_source, source_barrier

from sim2act import app_owner_goals as own
from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    goal_card_versions,
    goal_cards,
    internal_instances,
    internal_run_bindings,
    resources,
    runs,
)
from sim2act.errors import DomainError


def own_goal(rid):
    return dict(title="New material literal lookup", goal="Retrieve exact full Gamma lines in this material",
        known=["Case-sensitive matching"], assumptions=["Owner supplies the term"],
        unresolved=["Meaning and obligations require human judgement"],
        constraints=["Keep all matching lines and exact line numbers"],
        acceptance_checks=["Compare citations with this new material"], resource_refs=[rid])


def own_source_barrier(data, old):
    """Also forbid both initial GoalCard bodies, including the old target's."""
    with data[0].tx() as c:
        authored = {r["response"]["card_id"] for r in c.execute(select(delivery_graph_requests.c.snapshot).where(
            delivery_graph_requests.c.kind == own.KIND)).scalars()}
        initial = set(c.execute(select(goal_cards.c.id).where(goal_cards.c.project_id == data[4])).scalars()) - authored
    assert len(initial) == 2
    # Configure every rule before the first guarded checkout creates TEMP views.
    barrier = source_barrier(data, *old)
    barrier.rules["goal_card_versions"] = (goal_card_versions, "card_id", initial, {"snapshot"})
    return barrier


def setup_owner(env, *, run=True):
    data, aid, oldrel, oldinst, oldrun, target, rid, url = prepared(env)
    obj, _ = mint(data, url)
    made = bind(data, obj, binding(data, obj, target))
    release, instance = release_instance(data, made["id"])
    job = None
    return data, made, release, instance, job, (aid, oldrel, oldinst, oldrun), rid


def own_run(data, made, release, instance, term="Gamma", key="own-worker-input"):
    from sim2act.worker import Worker

    binding_fp = data[2].get(goal_path(made)).json()["binding_fingerprint"]
    queued = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        input={"term": term}, request_key=key, expected_owner_goal_binding_fingerprint=binding_fp))
    assert queued.status_code == 202, queued.text
    assert Worker(data[0], data[1], NoModel()).once()
    result = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{queued.json()['run_id']}")
    assert result.status_code == 200, result.text
    return result.json()


def goal_path(made):
    return f"/api/internal/apps/{made['id']}/owner-goals"


def save_goal(data, made, rid, key="own-goal-v1", goal=None, applicability=None):
    read = data[2].get(goal_path(made))
    assert read.status_code == 200, read.text
    head = read.json()["head"]
    body = dict(expected_candidate_fingerprint=made["candidate_fingerprint"],
        expected_goal_version=head["version"] if head else 0,
        expected_goal_fingerprint=head["fingerprint"] if head else None,
        expected_binding_fingerprint=read.json()["binding_fingerprint"],
        goal=goal or own_goal(rid), applicability=applicability or ["Only this authorized document and literal terms"],
        consent="AUTHOR_THIS_APPLICATION_OWN_GOAL_AND_SCOPE", request_key=key)
    result = data[2].post(goal_path(made), json=body)
    assert result.status_code == 201, result.text
    return result.json(), body


@pytest.mark.parametrize("reject", [False, True])
def test_new_own_goal_source_gone_cold_actual_evidence_and_exact_items(env, reject):
    data, made, release, instance, job, old, rid = setup_owner(env)
    assert state(data, instance)["content_access"] is False
    before = snapshot(data[0])
    saved, body = save_goal(data, made, rid)
    job = own_run(data, made, release, instance)
    before = snapshot(data[0])
    assert saved["card_id"] != data[6]["id"]
    assert data[2].get("/api/goal-cards/" + saved["card_id"]).json()["content"] == own_goal(rid)
    assert data[2].post(goal_path(made), json=body).json()["card_id"] == saved["card_id"]
    assert data[2].post(goal_path(made), json={**body, "applicability": ["different"]}).status_code == 409
    revoke_source(data)
    cold = Store(data[1].database_url, test_only=True)
    barrier = own_source_barrier(data, old)
    barrier.attach(cold)
    try:
        with barrier, TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            cold_data = (cold, data[1], client, *data[3:])
            review, _ = prepare(cold_data, release, instance, job)
            contract = review["payload"]["contract"]
            assert contract["goal"] == body["goal"] and contract["applicability"] == body["applicability"]
            assert contract["source_goal"]["origin"] == "THIS_APPLICATION_OWNER_AUTHORED"
            assert contract["source_goal"]["card_id"] == saved["card_id"]
            assert contract["evidence"][0]["run_id"] == job["id"]
            assert {i["id"] for i in contract["items"]} >= {"title", "goal", "applicability:0", "resource_scope", "technical_scope"}
            request = choice_body(review, reject)
            reply = client.post(f"/api/internal/instances/{instance['id']}/owner-review-requests", json=request)
            assert reply.status_code == 201, reply.text
            current = state(cold_data, instance, request["request_key"])
            assert current["owner_acceptance"] == ("REJECTED" if reject else "ACCEPTED")
            assert current["technical_semantic_status"] == "UNKNOWN" and current["formal_publication_enabled"] is False
            assert current["record"]["payload"]["choices"] == request["choices"]
            assert not barrier.blocked
        after = snapshot(data[0])
        for table in ["app_drafts", "internal_releases", "internal_instances", "internal_instance_data", "principals"]:
            assert before[table] == after[table]
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize("change", ["goal", "applicability", "aba", "generic_card", "material", "instance", "new_result", "budget_below_cap"])
def test_exact_accepted_declaration_goes_stale_on_current_changes(env, change):
    data, made, release, instance, job, _, rid = setup_owner(env)
    saved, _ = save_goal(data, made, rid)
    job = own_run(data, made, release, instance)
    review, _ = prepare(data, release, instance, job)
    request = choice_body(review)
    assert data[2].post(f"/api/internal/instances/{instance['id']}/owner-review-requests", json=request).status_code == 201
    if change in {"goal", "applicability", "aba"}:
        next_goal = {**own_goal(rid), "goal": "Other criteria"} if change != "applicability" else own_goal(rid)
        save_goal(data, made, rid, "own-goal-v2", next_goal, ["Different scope"])
        if change == "aba":
            save_goal(data, made, rid, "own-goal-v3", own_goal(rid))
    elif change == "generic_card":
        updated = data[2].put("/api/goal-cards/" + saved["card_id"], json={**own_goal(rid),
            "goal": "generic explicit edit", "expected_version": 1})
        assert updated.status_code == 200, updated.text
    elif change == "new_result":
        own_run(data, made, release, instance, "Alpha", "newer-result")
    elif change == "budget_below_cap":
        # Current authority budget is below its frozen 64000 cap; source denial is STALE.
        with TestClient(create_app(data[0], replace(data[1], max_total_tokens=63000))) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            value = state((data[0], data[1], client, *data[3:]), instance, request["request_key"])
            assert value["owner_acceptance"] == "STALE", value
            assert value["recovered"]["status"] == "ACCEPTED"
        return
    else:
        with data[0].tx() as c:
            if change == "material":
                c.execute(update(resources).where(resources.c.id == rid).values(content="changed"))
            else:
                c.execute(update(internal_instances).where(internal_instances.c.id == instance["id"]).values(revision=2))
    current = state(data, instance, request["request_key"])
    assert current["owner_acceptance"] == "STALE", current
    assert current["recovered"]["status"] == "ACCEPTED" and "payload" not in current["recovered"]


@pytest.mark.parametrize("mutation", ["refs", "constraints", "checks", "scope", "candidate", "prior", "owner"])
def test_invalid_own_goal_does_not_partially_write(env, mutation):
    data, made, _, _, _, _, rid = setup_owner(env, run=False)
    body = dict(expected_candidate_fingerprint=made["candidate_fingerprint"], expected_goal_version=0,
        expected_goal_fingerprint=None, expected_binding_fingerprint=None, goal=own_goal(rid),
        applicability=["This document"], consent="AUTHOR_THIS_APPLICATION_OWN_GOAL_AND_SCOPE", request_key="bad-own-goal")
    if mutation == "refs":
        body["goal"]["resource_refs"] = [data[5]]
    elif mutation == "constraints":
        body["goal"]["constraints"] = []
    elif mutation == "checks":
        body["goal"]["acceptance_checks"] = []
    elif mutation == "scope":
        body["applicability"] = []
    elif mutation == "candidate":
        body["expected_candidate_fingerprint"] = "0" * 64
    elif mutation == "prior":
        body["expected_goal_version"] = 1
    else:
        data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    before = snapshot(data[0])
    reply = data[2].post(goal_path(made), json=body)
    assert reply.status_code in {400, 403, 409, 422}, reply.text
    assert snapshot(data[0]) == before


def test_goal_version_seal_fault_and_write_fault_rollback(env):
    data, made, _, _, _, _, rid = setup_owner(env, run=False)
    saved, body = save_goal(data, made, rid)
    before = snapshot(data[0])

    def fail(conn, cursor, sql, args, context, many):
        if sql.startswith("INSERT INTO delivery_graph_requests"):
            raise RuntimeError("synthetic own goal seal failure")

    event.listen(data[0].engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="synthetic own goal"):
            save_goal(data, made, rid, "new-version")
    finally:
        event.remove(data[0].engine, "before_cursor_execute", fail)
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made["id"],
            delivery_graph_requests.c.kind == own.KIND + "_seal"))
    assert data[2].get(goal_path(made)).status_code == 409


def test_final_goal_write_rechecks_current_authority(env, monkeypatch):
    data, made, _, _, _, _, rid = setup_owner(env, run=False)
    actual = time.time
    expired = False
    monkeypatch.setattr(own.logic, "time", SimpleNamespace(time=lambda: actual() + 90000 if expired else actual()))

    def after_version(conn, cursor, sql, args, context, many):
        nonlocal expired
        if sql.startswith("INSERT INTO goal_card_versions"):
            expired = True

    before = snapshot(data[0])
    event.listen(data[0].engine, "after_cursor_execute", after_version)
    try:
        with pytest.raises(AssertionError, match="403"):
            save_goal(data, made, rid)
    finally:
        event.remove(data[0].engine, "after_cursor_execute", after_version)
    assert expired and snapshot(data[0]) == before


def review_body(data, release, instance, job, key="prepare-own-current"):
    return dict(command="PREPARE", request_key=key, expected_sequence=state(data, instance)["sequence"],
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"], run_ids=[job["id"]])


def test_goal_before_run_requires_explicit_exact_binding_and_preserves_history(env):
    data, made, release, instance, _, _, rid = setup_owner(env)
    unbound = run_input(data, release, instance, {"term": "Gamma"}, "before-own-goal")
    saved, _ = save_goal(data, made, rid)
    before = snapshot(data[0])
    path = f"/api/internal/instances/{instance['id']}/runs"
    base = dict(expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
                input={"term": "Gamma"}, request_key="missing-current-own-goal")
    for fp in (None, "0" * 64):
        request = {**base, **({"expected_owner_goal_binding_fingerprint": fp} if fp else {})}
        reply = data[2].post(path, json=request)
        assert reply.status_code == 409, reply.text
        assert snapshot(data[0]) == before
    assert data[2].get(path + "/" + unbound["id"]).json()["status"] == "SUCCEEDED"
    assert data[2].post(f"/api/internal/instances/{instance['id']}/owner-review-requests",
                      json=review_body(data, release, instance, unbound)).status_code == 409
    new = own_run(data, made, release, instance, key="after-own-goal")
    prepare(data, release, instance, new)
    save_goal(data, made, rid, "own-revision-2", {**own_goal(rid), "goal": "Revision 2 criteria"})
    stale = state(data, instance)
    assert stale["owner_acceptance"] == "STALE" and stale["content_access"] is False
    assert stale["prepare_current"]["source_goal"]["version"] == 2
    assert "record" not in stale and "current" not in stale
    history = data[2].get(path + "/" + new["id"])
    assert history.status_code == 200 and history.json()["status"] == "SUCCEEDED", history.text
    assert data[2].post(f"/api/internal/instances/{instance['id']}/owner-review-requests",
                      json=review_body(data, release, instance, new, "reject-old-goal-run")).status_code == 409
    fresh = own_run(data, made, release, instance, "final", "revision-2-worker")
    review, _ = prepare(data, release, instance, fresh, "revision-2-prepare")
    assert review["payload"]["contract"]["source_goal"]["version"] == saved["goal_version"] + 1
    assert review["payload"]["contract"]["evidence"][0]["run_id"] == fresh["id"]


@pytest.mark.parametrize("moment", ["queued", "computed", "typed_append"])
def test_goal_change_cannot_commit_old_worker_result(env, monkeypatch, moment):
    from sim2act import app_jobs
    from sim2act.worker import Worker

    data, made, release, instance, _, _, rid = setup_owner(env)
    saved, _ = save_goal(data, made, rid)
    queued = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        expected_owner_goal_binding_fingerprint=saved["binding_fingerprint"],
        input={"term": "Gamma"}, request_key="old-goal-worker"))
    assert queued.status_code == 202, queued.text
    changed = False
    def revise():
        nonlocal changed
        save_goal(data, made, rid, "revision-during-run", {**own_goal(rid), "goal": "new goal"})
        changed = True
    def after_typed(conn, cursor, sql, args, context, many):
        nonlocal changed
        if sql.startswith("INSERT INTO internal_instance_data"):
            conn.execute(update(goal_cards).where(goal_cards.c.id == saved["card_id"]).values(version=2))
            changed = True
    if moment == "queued":
        revise()
    elif moment == "computed":
        actual_compute = app_jobs.compute
        def compute(*args, **kwargs):
            result = actual_compute(*args, **kwargs)
            revise()
            return result
        monkeypatch.setattr(app_jobs, "compute", compute)
    else:
        event.listen(data[0].engine, "after_cursor_execute", after_typed)
    before = snapshot(data[0])["internal_instance_data"]
    try:
        assert Worker(data[0], data[1], NoModel()).once()
    finally:
        if moment == "typed_append":
            event.remove(data[0].engine, "after_cursor_execute", after_typed)
    actual = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{queued.json()['run_id']}")
    assert actual.status_code == 200, actual.text
    assert actual.json()["status"] == "FAILED", actual.text
    assert changed and snapshot(data[0])["internal_instance_data"] == before
    assert actual.json()["result_version"] is None


def test_all100_original_own_goal_items_are_required_in_exact_order(env):
    data, made, release, instance, _, _, rid = setup_owner(env)
    goal = own_goal(rid)
    for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        goal[field] = [f"{field} original criterion {n}" for n in range(16)]
    save_goal(data, made, rid, goal=goal, applicability=[f"scope {n}" for n in range(16)])
    job = own_run(data, made, release, instance)
    review, _ = prepare(data, release, instance, job)
    body = choice_body(review)
    assert len(body["choices"]) == len(review["payload"]["contract"]["items"]) == 100
    path = f"/api/internal/instances/{instance['id']}/owner-review-requests"
    before = snapshot(data[0])
    for choices in (body["choices"][:-1], list(reversed(body["choices"]))):
        reply = data[2].post(path, json={**body, "choices": choices})
        assert reply.status_code == 400 and reply.json()["error"]["code"] == "INVALID_INPUT", reply.text
        assert snapshot(data[0]) == before
    reply = data[2].post(path, json=body)
    assert reply.status_code == 201, reply.text
    assert state(data, instance)["owner_acceptance"] == "ACCEPTED"


@pytest.mark.parametrize("tamper", ["missing_fp", "missing_ref", "null", "extra", "bool_version"])
def test_malformed_owned_run_ref_is_controlled_and_worker_fails_closed(env, tamper):
    from sim2act.contracts import Limits
    from sim2act.worker import Worker

    data, made, release, instance, _, _, rid = setup_owner(env)
    saved, _ = save_goal(data, made, rid)
    before = snapshot(data[0])["internal_instance_data"]
    reply = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        expected_owner_goal_binding_fingerprint=saved["binding_fingerprint"], input={"term": "Gamma"}, request_key="polluted-goal-ref"))
    assert reply.status_code == 202, reply.text
    jid = reply.json()["run_id"]
    with data[0].tx() as c:
        s = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == jid)).scalar_one()
        if tamper == "missing_fp":
            s.pop("owner_goal_binding_fingerprint")
        elif tamper == "missing_ref":
            s.pop("owner_goal")
        elif tamper == "null":
            s["owner_goal"] = None
        elif tamper == "extra":
            s["owner_goal"]["extra"] = True
        else:
            s["owner_goal"]["goal_version"] = True
        limits = Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})
        draft = c.execute(select(app_drafts).where(
            app_drafts.c.id == made["id"])).mappings().one()
        with pytest.raises(DomainError):
            own.verify_frozen_run(data[0], c, data[3], draft, limits, s)
        # Reseal only the deliberately corrupt raw queue, exercising actual Worker rejection.
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == jid).values(snapshot=s, fingerprint=fingerprint(s)))
        c.execute(update(runs).where(runs.c.id == jid).values(fingerprint=fingerprint(s)))
    assert Worker(data[0], data[1], NoModel()).once()
    with data[0].tx() as c:
        current = c.execute(select(runs.c.status, runs.c.error).where(runs.c.id == jid)).mappings().one()
    assert current["status"] == "FAILED" and current["error"]["code"] == "VERSION_CONFLICT", current
    response = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{jid}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "VERSION_CONFLICT", response.text
    assert snapshot(data[0])["internal_instance_data"] == before


def test_budget_change_stales_exact_goal_signature_even_above_frozen_cap(env):
    store = env[0]
    settings = replace(env[1], max_total_tokens=51200)
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        data, made, release, instance, _, _, rid = setup_owner((store, settings, client, *env[3:]))
        save_goal(data, made, rid)
        job = own_run(data, made, release, instance)
        review, _ = prepare(data, release, instance, job)
        body = choice_body(review)
        path = f"/api/internal/instances/{instance['id']}/owner-review-requests"
        before = snapshot(store)
        with TestClient(create_app(store, replace(settings, max_total_tokens=63000))) as raised:
            raised.headers["Authorization"] = "Bearer synthetic-test-A"
            raised_data = (store, settings, raised, *data[3:])
            current = state(raised_data, instance)
            assert current["owner_acceptance"] == "STALE" and not current["content_access"]
            assert current["prepare_current"]["current_limits"]["max_total_tokens"] == 63000
            assert raised.get(goal_path(made)).status_code == 200  # Authority still valid, cap 51200.
            reply = raised.post(path, json=body)
            assert reply.status_code == 409, reply.text
            assert snapshot(store) == before
            fresh, _ = prepare(raised_data, release, instance, job, "prepare-higher-budget")
            assert fresh["payload"]["contract"]["current_limits"]["max_total_tokens"] == 63000
