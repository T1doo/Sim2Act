"""Actual owner-only edit protection, recovery and serializable races."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import update
from test_column_patches import setup, url
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_run_dispatch_owner import assert_no_ledger_read, statements

from sim2act import delivery_graph_apps as graph
from sim2act import manual_locks as locks
from sim2act.db import fingerprint, grants, projects, resources
from sim2act.errors import DomainError


def body(anchor, locked=True, rev=0, key="edit-lock"):
    node = next(n for n in anchor["graph"]["nodes"] if n["key"] == "action:aggregate")
    return dict(expected_graph_fingerprint=anchor["graph_fingerprint"], expected_graph_revision=anchor["graph_revision"],
        change=dict(node_id=node["id"], expected_revision=node["revision"], expected_content_fingerprint=node["content_fingerprint"]),
        expected_lock_revision=rev, locked=locked, request_key=key, consent=locks.CONSENT)


def base(env, aid):
    return url(env, aid).removesuffix("column-patches") + "manual-locks"


def derive(env, aid, key):
    draft = env[2].get(f"/api/apps/{aid}").json()
    reply = env[2].post(url(env, aid).removesuffix("column-patches") + "derive",
        json=dict(expected_candidate_fingerprint=draft["fingerprint"], request_key=key))
    assert reply.status_code == 201, reply.text
    return reply.json()


def test_real_lock_conflict_unlock_new_exact_plan_and_read_checks(env):
    aid, _, anchor, patch, _ = setup(env)
    before = snapshot(env)
    request = body(anchor)
    reply = env[2].post(base(env, aid), json=request)
    assert reply.status_code == 201, reply.text
    assert reply.json()["lock"]["revision"] == 1
    for table in before:
        if table not in {"delivery_graph_locks", "delivery_graph_requests"}:
            assert fingerprint(before[table]) == fingerprint(snapshot(env)[table]), table
    after = snapshot(env)
    assert env[2].post(base(env, aid), json=request).json()["cached"]
    assert env[2].get(base(env, aid) + "/receipt", params={"request_key": request["request_key"]}).json()["is_current"]
    assert fingerprint(after) == fingerprint(snapshot(env))
    locked = derive(env, aid, "locked-anchor")
    patch["expected_graph_fingerprint"] = locked["graph_fingerprint"]
    patch["change"] = body(locked)["change"]
    before = snapshot(env)
    denied = env[2].post(url(env, aid), json=patch)
    assert denied.status_code == 400 and denied.json()["error"]["code"] == "LOCK_CONFLICT"
    assert fingerprint(before) == fingerprint(snapshot(env))
    unlock = body(locked, False, 1, "edit-unlock")
    reply = env[2].post(base(env, aid), json=unlock)
    assert reply.status_code == 201, reply.text
    assert reply.json()["lock"]["revision"] == 2
    old = env[2].post(base(env, aid), json=request)
    assert old.status_code == 201 and old.json()["receipt_status"] == "SUPERSEDED"
    assert old.json()["is_current"] is False
    unlocked = derive(env, aid, "unlocked-anchor")
    patch["expected_graph_fingerprint"] = unlocked["graph_fingerprint"]
    patch["change"] = body(unlocked)["change"]
    patch["request_key"] = "after-unlock"
    made = env[2].post(url(env, aid), json=patch)
    assert made.status_code == 201, made.text
    checked = env[2].post(url(env, aid) + "/after-unlock/checks", json=dict(expected_patch_fingerprint=made.json()["patch_fingerprint"], request_key="exact-check"))
    assert checked.status_code == 201, checked.text
    assert checked.json()["outputs"]["baseline"]["sum"] == "30"
    assert checked.json()["outputs"]["patched"]["sum"] == "15"
    assert checked.json()["publishable"] is False


@pytest.mark.parametrize("field,value", [("expected_graph_revision", True), ("expected_lock_revision", True),
    ("expected_lock_revision", 9), ("expected_graph_revision", 9), ("consent", ""), ("locked", 1),
    ("request_key", "bad\x00key"), ("expected_graph_fingerprint", "0" * 64)])
def test_bad_versions_confirmation_and_keys_zero_writes(env, field, value):
    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    request[field] = value
    before = snapshot(env)
    reply = env[2].post(base(env, aid), json=request)
    assert reply.status_code in {400, 409, 422}, reply.text
    assert fingerprint(before) == fingerprint(snapshot(env))


@pytest.mark.parametrize("change", ["foreign", "transfer", "revoke", "source"])
def test_current_authority_and_source_gate_precede_recovery(env, change):
    aid, rid, anchor, _, _ = setup(env)
    request = body(anchor)
    assert env[2].post(base(env, aid), json=request).status_code == 201
    if change == "foreign":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    else:
        with env[0].tx() as c:
            if change == "transfer":
                c.execute(update(projects).where(projects.c.id == env[5]).values(owner_id=env[4]))
            elif change == "revoke":
                c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
            else:
                import hashlib
                text = "amount,quantity\n9,8\n"
                c.execute(update(resources).where(resources.c.id == rid).values(content=text, hash=hashlib.sha256(text.encode()).hexdigest()))
    before = snapshot(env)
    for suffix, verb in [("", "post"), ("", "get"), ("/receipt", "get")]:
        with statements(env[0]) as sql:
            reply = (env[2].post(base(env, aid), json=request) if verb == "post" else
                     env[2].get(base(env, aid) + suffix, params={"request_key": request["request_key"]} if suffix else {}))
        assert reply.status_code in {403, 409}, reply.text
        if change in {"foreign", "transfer"}:
            assert_no_ledger_read(sql)
    assert fingerprint(before) == fingerprint(snapshot(env))


def test_same_key_changed_body_and_aba_cas_preserve_history(env):
    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    assert env[2].post(base(env, aid), json=request).status_code == 201
    before = snapshot(env)
    changed = {**request, "locked": False}
    assert env[2].post(base(env, aid), json=changed).status_code == 409
    assert fingerprint(before) == fingerprint(snapshot(env))
    locked = derive(env, aid, "for-unlock")
    assert env[2].post(base(env, aid), json=body(locked, False, 1, "unlock")).status_code == 201
    unlocked = derive(env, aid, "for-relock")
    assert unlocked["graph_fingerprint"] == anchor["graph_fingerprint"]
    before = snapshot(env)
    assert env[2].post(base(env, aid), json={**request, "request_key": "stale-aba"}).status_code == 409
    assert env[2].post(base(env, aid), json=body(unlocked, True, 0, "bad-cas")).status_code == 409
    assert fingerprint(before) == fingerprint(snapshot(env))
    assert env[2].post(base(env, aid), json=body(unlocked, True, 2, "relock")).status_code == 201
    history = env[2].get(base(env, aid)).json()["history"]
    assert [r["request_key"] for r in history if r["is_current"]] == ["relock"]


@pytest.mark.parametrize("race", ["lock-lock", "lock-modify", "unlock-unlock"])
def test_actual_concurrent_lock_modify_unlock(env, race):
    aid, _, anchor, patch, _ = setup(env)
    if race == "unlock-unlock":
        locks.submit(env[0], env[3], env[5], aid, body(anchor), limits(env))
        anchor = derive(env, aid, "race-unlock")
    requests = [body(anchor, race != "unlock-unlock", int(race == "unlock-unlock"), f"race-{i}") for i in range(2)]
    import threading
    barrier = threading.Barrier(2)
    def run(index):
        barrier.wait(timeout=10)
        try:
            if race == "lock-modify" and index == 1:
                from sim2act.column_patches import DefinitionInput, propose
                return propose(env[0], env[3], env[5], aid, DefinitionInput(**patch), limits(env))
            return locks.submit(env[0], env[3], env[5], aid, requests[index], limits(env))
        except DomainError as e:
            return e.code
    with ThreadPoolExecutor(2) as pool:
        result = list(pool.map(run, [0, 1]))
    if race == "lock-modify":
        # If modification wins first, its immutable draft may coexist with the later
        # lock; its future checks must revalidate the now-stale graph/lock baseline.
        if isinstance(result[1], dict):
            from sim2act.column_patches import CheckInput, check
            with pytest.raises(DomainError):
                check(env[0], env[3], env[5], aid, patch["request_key"], CheckInput(expected_patch_fingerprint=result[1]["patch_fingerprint"], request_key="stale-check"), limits(env))
        else:
            assert result[1] == "VERSION_CONFLICT"
    else:
        assert sum(isinstance(r, dict) for r in result) == 1
        assert "VERSION_CONFLICT" in result


def test_old_internal_lock_compatible_public_unlock_and_noop_rejected(env):
    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    canonical = graph.LockInput(**{k: request[k] for k in ["expected_graph_fingerprint", "change", "locked", "request_key"]})
    graph.set_lock(env[0], env[3], env[5], aid, canonical, limits(env))
    locked = derive(env, aid, "internal-locked")
    state = env[2].get(base(env, aid)).json()
    assert next(n for n in state["nodes"] if n["node_id"] == request["change"]["node_id"])["lock_revision"] == 1
    assert env[2].post(base(env, aid), json=body(locked, False, 1, "public-unlock")).status_code == 201
    unlocked = derive(env, aid, "no-op")
    before = snapshot(env)
    assert env[2].post(base(env, aid), json=body(unlocked, False, 2, "no-op")).status_code == 400
    assert fingerprint(before) == fingerprint(snapshot(env))


@pytest.mark.parametrize("kind", [locks.KIND, locks.KIND + "_seal", "lock"])
def test_tampered_accepted_lock_ledger_is_not_current_proof(env, kind):
    from sqlalchemy import select

    from sim2act.db import delivery_graph_requests as requests

    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    assert env[2].post(base(env, aid), json=request).status_code == 201
    with env[0].tx() as c:
        row = c.execute(select(requests).where(requests.c.app_id == aid, requests.c.kind == kind)).mappings().one()
        import copy
        value = copy.deepcopy(row["snapshot"])
        value["response"]["lock"]["revision"] = 91
        c.execute(update(requests).where(requests.c.app_id == aid, requests.c.kind == kind).values(snapshot=value, fingerprint=fingerprint(value)))
    before = snapshot(env)
    reply = env[2].post(base(env, aid), json=request)
    assert reply.status_code == 409, reply.text
    assert fingerprint(before) == fingerprint(snapshot(env))


def test_cold_store_recovery_after_derive_and_source_change_invalidates(env):
    import hashlib

    from sim2act.db import Store

    aid, rid, anchor, _, _ = setup(env)
    request = body(anchor)
    locks.submit(env[0], env[3], env[5], aid, request, limits(env))
    derive(env, aid, "cold-locked")
    store = Store(env[1].database_url, test_only=True)
    store.engine = store.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        before = snapshot(env)
        result = locks.submit(store, env[3], env[5], aid, request, limits(env))
        assert result["cached"] and result["is_current"]
        assert fingerprint(before) == fingerprint(snapshot(env))
    finally:
        store.engine.dispose()
    with env[0].tx() as c:
        text = "amount,quantity\n30,25\n"
        c.execute(update(resources).where(resources.c.id == rid).values(content=text, hash=hashlib.sha256(text.encode()).hexdigest()))
    before = snapshot(env)
    assert env[2].post(base(env, aid), json=request).status_code == 409
    assert env[2].get(base(env, aid)).status_code == 409
    assert env[2].get(base(env, aid) + "/receipt", params={"request_key": request["request_key"]}).status_code == 409
    assert fingerprint(before) == fingerprint(snapshot(env))


def test_pg_minimum_crud_role_manual_lock_and_cold_receipt(env, runtime_role):
    from sim2act.db import Store

    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    store = Store(runtime_role, test_only=True)
    try:
        with statements(store) as sql, pytest.raises(DomainError):
            locks.submit(store, env[4], env[5], aid, request, limits(env))
        assert_no_ledger_read(sql)
        made = locks.submit(store, env[3], env[5], aid, request, limits(env))
        before = snapshot(env)
        assert made["lock"]["revision"] == 1
        assert locks.inspect(store, env[3], env[5], aid, limits(env), request["request_key"])["is_current"]
        assert locks.submit(store, env[3], env[5], aid, request, limits(env))["cached"]
        assert fingerprint(before) == fingerprint(snapshot(env))
    finally:
        store.engine.dispose()


def test_client_identity_fields_and_underived_report_cannot_bypass_lock_preflight(env, tmp_path):
    from test_delivery_graph_apps import report_project

    aid, _, anchor, _, _ = setup(env)
    request = body(anchor)
    before = snapshot(env)
    assert env[2].post(base(env, aid), json={**request, "principal_id": env[4]}).status_code == 422
    assert fingerprint(before) == fingerprint(snapshot(env))
    report, *_ = report_project(env, tmp_path)
    before = snapshot(env)
    reply = env[2].get(base(env, report["id"]))
    assert reply.status_code == 409 and reply.json()["error"]["code"] == "VERSION_CONFLICT", reply.text
    assert fingerprint(before) == fingerprint(snapshot(env))
