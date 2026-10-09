"""Owner-protected existing Report graph, actual original presentation edits."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, update
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_manual_locks import derive
from test_report_presentations import env as env
from test_report_presentations import prepared

from sim2act import manual_locks
from sim2act.api import create_app
from sim2act.db import Store, app_drafts, fingerprint, grants, resources
from sim2act.db import delivery_graph_locks as lock_rows
from sim2act.db import delivery_graph_requests as requests


def body(anchor, locked=True, rev=0, key="report-view-lock"):
    node = next(n for n in anchor["graph"]["nodes"] if n["key"] == "view:text:decision")
    return dict(
        expected_graph_fingerprint=anchor["graph_fingerprint"],
        expected_graph_revision=anchor["graph_revision"],
        change=dict(
            node_id=node["id"],
            expected_revision=node["revision"],
            expected_content_fingerprint=node["content_fingerprint"],
        ),
        expected_lock_revision=rev,
        locked=locked,
        request_key=key,
        consent=manual_locks.CONSENT,
    )


def setup(env, tmp_path):
    app, anchor, presentation, definition, output, wires = prepared(env, tmp_path)
    base = presentation.removesuffix("report-presentations")
    return app, anchor, base, definition, output, wires


def assert_unchanged(env, before):
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_report_lock_blocks_actual_original_edit_unlock_new_plan_and_readback(env, tmp_path):
    app, anchor, base, definition, output, wires = setup(env, tmp_path)
    before = snapshot(env)
    reply = env[2].post(base + "manual-locks", json=body(anchor))
    assert reply.status_code == 201, reply.text
    assert reply.json()["lock"]["logical_key"] == "view:text:decision"
    assert reply.json()["lock"]["locked"] is True
    after = snapshot(env)
    for table in before:
        if table not in {"delivery_graph_locks", "delivery_graph_requests"}:
            assert before[table] == after[table], table
    locked = derive(env, app["id"], "report-locked-anchor")
    before = snapshot(env)
    denied = env[2].post(
        base + "plans",
        json=dict(
            expected_graph_fingerprint=locked["graph_fingerprint"],
            request_key="locked-view-plan",
            changes=[body(locked)["change"]],
        ),
    )
    assert denied.status_code == 400 and denied.json()["error"]["code"] == "LOCK_CONFLICT", (
        denied.text
    )
    definition["expected_graph_fingerprint"] = locked["graph_fingerprint"]
    denied = env[2].post(base + "report-presentations", json=definition)
    assert denied.status_code == 409
    assert_unchanged(env, before)
    unlocked = env[2].post(base + "manual-locks", json=body(locked, False, 1, "report-view-unlock"))
    assert unlocked.status_code == 201, unlocked.text
    anchor = derive(env, app["id"], "report-unlocked-anchor")
    plan = env[2].post(
        base + "plans",
        json=dict(
            expected_graph_fingerprint=anchor["graph_fingerprint"],
            request_key="unlocked-view-plan",
            changes=[body(anchor)["change"]],
        ),
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["scope_expansion"]["status"] in {"PENDING", "BLOCKED_PARTIAL"}
    definition.update(
        expected_graph_fingerprint=anchor["graph_fingerprint"],
        plan_key="unlocked-view-plan",
        expected_plan_fingerprint=plan.json()["native_outer_fingerprint"],
        request_key="unlocked-explanation",
    )
    patch = env[2].post(base + "report-presentations", json=definition)
    assert patch.status_code == 201, patch.text
    check = env[2].post(
        base + "report-presentations/unlocked-explanation/checks",
        json=dict(
            expected_patch_fingerprint=patch.json()["patch_fingerprint"],
            request_key="unlocked-readback",
        ),
    )
    assert check.status_code == 201, check.text
    assert check.json()["text"] == output["explanation"]
    assert check.json()["display_readback_status"] == "PASS"
    assert (
        check.json()["semantic_status"] == "UNKNOWN"
        and check.json()["owner_acceptance"] == "PENDING"
    )
    assert check.json()["project_revalidation_status"] in {"PENDING", "BLOCKED_PARTIAL"}
    assert len(wires) == 4  # Only the original synthetic Report fixture requests.
    assert env[2].get(f"/api/apps/{app['id']}").json()["fingerprint"] == app["fingerprint"]


def test_report_lock_cold_store_same_key_recovery_and_superseded_history(env, tmp_path):
    app, anchor, base, _, _, _ = setup(env, tmp_path)
    request = body(anchor)
    accepted = env[2].post(base + "manual-locks", json=request)
    assert accepted.status_code == 201, accepted.text
    before = snapshot(env)
    cold = Store(env[1].database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    from fastapi.testclient import TestClient

    with TestClient(create_app(cold, env[1])) as client:
        client.headers.update({"Authorization": "Bearer synthetic-test-A"})
        replay = client.post(base + "manual-locks", json=request)
        assert replay.status_code == 201 and replay.json()["cached"] is True, replay.text
        read = client.get(
            base + "manual-locks/receipt", params={"request_key": request["request_key"]}
        )
        assert read.status_code == 200 and read.json()["is_current"] is True, read.text
        assert client.get(base + "manual-locks").json()["needs_derive"] is True
    cold.engine.dispose()
    assert_unchanged(env, before)
    locked = derive(env, app["id"], "cold-report-lock")
    assert (
        env[2]
        .post(base + "manual-locks", json=body(locked, False, 1, "cold-report-unlock"))
        .status_code
        == 201
    )
    history = env[2].get(base + "manual-locks").json()["history"]
    assert any(h["receipt_status"] == "SUPERSEDED" and h["is_current"] is False for h in history)


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "graph",
        "graph_revision",
        "node_revision",
        "node_hash",
        "node_id",
        "lock_revision",
        "consent",
        "locked_int",
        "graph_bool",
        "extra",
        "no_change",
    ],
)
def test_invalid_report_lock_rejected_before_any_write(env, tmp_path, mutation):
    _, anchor, base, _, _, _ = setup(env, tmp_path)
    request = body(anchor)
    if mutation == "candidate":
        with env[0].tx() as c:
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == anchor["app_id"])
                .values(fingerprint="0" * 64)
            )
    elif mutation == "graph":
        request["expected_graph_fingerprint"] = "0" * 64
    elif mutation == "graph_revision":
        request["expected_graph_revision"] += 1
    elif mutation == "node_revision":
        request["change"]["expected_revision"] += 1
    elif mutation == "node_hash":
        request["change"]["expected_content_fingerprint"] = "0" * 64
    elif mutation == "node_id":
        request["change"]["node_id"] = "node_" + "0" * 32
    elif mutation == "lock_revision":
        request["expected_lock_revision"] = 1
    elif mutation == "consent":
        request["consent"] = "AUTO_CONFIRM"
    elif mutation == "locked_int":
        request["locked"] = 1
    elif mutation == "graph_bool":
        request["expected_graph_revision"] = True
    elif mutation == "extra":
        request["grant"] = "automatic"
    elif mutation == "no_change":
        request["locked"] = False
    before = snapshot(env)
    reply = env[2].post(base + "manual-locks", json=request)
    assert reply.status_code in {400, 409, 422}, reply.text
    assert_unchanged(env, before)


@pytest.mark.parametrize(
    "mutation", ["other_owner", "other_project", "revoke", "source", "seal", "lock", "same_key"]
)
def test_report_lock_authority_and_saved_tamper_fail_closed(env, tmp_path, mutation):
    app, anchor, base, _, _, _ = setup(env, tmp_path)
    request = body(anchor)
    accepted = env[2].post(base + "manual-locks", json=request)
    assert accepted.status_code == 201, accepted.text
    route = base + "manual-locks/receipt?request_key=report-view-lock"
    if mutation == "other_owner":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif mutation == "other_project":
        route = route.replace(env[5], env[0].project(env[3], "other Report project"))
    elif mutation == "revoke":
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == env[3],
                    grants.c.resource_id == app["candidate"]["report_proof"]["target_resource_id"],
                )
                .values(revoked=True)
            )
    elif mutation == "source":
        with env[0].tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == app["candidate"]["report_proof"]["target_resource_id"])
                .values(content="changed")
            )
    elif mutation in {"seal", "lock"}:
        table = requests if mutation == "seal" else lock_rows
        with env[0].tx() as c:
            query = select(table).where(table.c.app_id == app["id"])
            if mutation == "seal":
                query = query.where(table.c.kind == "manual_edit_lock_seal")
            row = c.execute(query).mappings().one()
            value = copy.deepcopy(row["snapshot"])
            if mutation == "seal":
                value["response"]["lock"]["locked"] = False
            else:
                value["locked"] = False
            where = (
                (table.c.kind == row["kind"])
                if mutation == "seal"
                else (table.c.node_id == row["node_id"])
            )
            where = where & (table.c.app_id == row["app_id"])
            c.execute(
                update(table).where(where).values(snapshot=value, fingerprint=fingerprint(value))
            )
    elif mutation == "same_key":
        request["locked"] = False
    before = snapshot(env)
    reply = (
        env[2].post(base + "manual-locks", json=request)
        if mutation == "same_key"
        else env[2].get(route)
    )
    assert reply.status_code in {400, 403, 409}, reply.text
    assert_unchanged(env, before)


def test_report_lock_two_real_connections_have_one_revision_winner(env, tmp_path):
    app, anchor, _, _, _, _ = setup(env, tmp_path)
    from sim2act.errors import DomainError

    def submit(key):
        try:
            return manual_locks.submit(
                env[0],
                env[3],
                env[5],
                app["id"],
                manual_locks.LockInput.model_validate(body(anchor, key=key)),
                limits(env),
            )["lock"]["revision"]
        except DomainError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ["race-report-a", "race-report-b"]))
    assert sorted(map(str, results)) == ["1", "VERSION_CONFLICT"]


def test_report_lock_pg_business_crud_role_and_cold_receipt(env, tmp_path, runtime_role):
    app, anchor, _, _, _, _ = setup(env, tmp_path)
    store = Store(runtime_role, test_only=True)
    try:
        request = manual_locks.LockInput.model_validate(body(anchor))
        made = manual_locks.submit(store, env[3], env[5], app["id"], request, limits(env))
        assert made["lock"]["revision"] == 1
        before = snapshot(env)
        assert (
            manual_locks.inspect(
                store, env[3], env[5], app["id"], limits(env), request.request_key
            )["is_current"]
            is True
        )
        assert (
            manual_locks.submit(store, env[3], env[5], app["id"], request, limits(env))["cached"]
            is True
        )
        assert_unchanged(env, before)
    finally:
        store.engine.dispose()
