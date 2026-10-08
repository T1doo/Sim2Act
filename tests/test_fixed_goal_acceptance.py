"""Prospective finite goal success, source eligibility and legacy PARTIAL isolation."""

import copy
import time

import httpx
import pytest
from sqlalchemy import select, update
from test_natural_activation_flow import approved, confirmation, setup, wire
from test_natural_goal_planning import response
from test_natural_receipt_candidate import accepted, table_snapshot

from sim2act.db import Store, fingerprint, operations, run_contracts, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def prepared(env, kind="sum_quantity_z", finish=True, fail_after_effect=False):
    value = setup(env)
    store, settings, client, user, other, pid, resource, cards = value
    session, _ = approved(value)
    card = cards[kind]
    body = {
        "expected_version": card["version"],
        "expected_fingerprint": card["fingerprint"],
        "request_key": "fixed-goal",
    }
    path = f"/api/natural-activations/{session['id']}/goal-cards/{card['id']}/fixed-goal-runs"
    result = client.post(path, json=body)
    assert result.status_code == 202, result.text
    rid = result.json()["run_id"]
    sent = []

    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value, kind)))

    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    waiting = client.get("/api/runs/" + rid).json()
    assert waiting["status"] == "WAITING_APPROVAL" and not waiting["known_effects"]
    if finish:
        assert (
            client.post(
                "/api/runs/" + rid + "/confirm-natural-plan", json=confirmation(client, rid)
            ).status_code
            == 200
        )
        if fail_after_effect:
            from unittest.mock import patch

            from sim2act.goal_planner import dispatch

            def failure(*args, **kwargs):
                receipt = dispatch(*args, **kwargs)
                assert receipt["status"] == "VERIFIED"
                raise DomainError("VERIFICATION_FAILED", "Injected failure after real effect")

            with patch("sim2act.goal_planner.dispatch", failure):
                assert worker.once()
        else:
            assert worker.once()
    return value, session, rid, sent, worker, path, body


@pytest.mark.parametrize("kind", ["read_preview", "sum_quantity_z"])
def test_explicit_whole_fixed_contract_and_cold_read_keep_owner_and_publish_pending(env, kind):
    value, _, rid, sent, _, path, body = prepared(env, kind)
    store, settings, client, user, *_ = value
    view = client.get("/api/runs/" + rid)
    assert view.status_code == 200, view.text
    view = view.json()
    report = view["result"]["task_acceptance"]
    assert (
        view["status"] == "SUCCEEDED" and view["result"]["goal_acceptance"] == "PASS_FIXED_CONTRACT"
    )
    assert report["whole_task_accepted"] is True and report["single_step_status"] == "VERIFIED"
    assert (
        report["scope"] == "EXACT_FIXED_SYNTHETIC_GOAL_ONLY"
        and report["owner_acceptance"] == "PENDING"
    )
    assert not report["formal_publication_enabled"] and not view["result"]["candidate_generated"]
    assert client.post(path, json=body).json()["run_id"] == rid
    cold = Store(settings.database_url, test_only=True)
    try:
        assert cold.inspect(user, rid) == view
    finally:
        cold.engine.dispose()
    assert len(sent) == 1
    if kind == "read_preview":
        assert client.get("/api/runs/" + rid + "/receipt-candidate-options").status_code == 400


def test_partial_effect_cannot_be_whole_success_or_candidate(env):
    value, _, rid, _, _, _, _ = prepared(env, fail_after_effect=True)
    store, _, client, *_ = value
    view = client.get("/api/runs/" + rid).json()
    assert view["status"] == "FAILED" and view["result"] is None
    assert len(view["known_effects"]) == 1 and view["known_effects"][0]["status"] == "VERIFIED"
    before = table_snapshot(store)
    assert client.get("/api/runs/" + rid + "/receipt-candidate-options").status_code == 400
    assert table_snapshot(store) == before


def test_prospective_mode_key_conflict_no_implicit_or_retroactive_acceptance(env):
    value, _, rid, _, _, path, body = prepared(env, finish=False)
    store, _, client, *_ = value
    before = table_snapshot(store)
    assert (
        client.post(path.replace("fixed-goal-runs", "planned-runs"), json=body).status_code == 409
    )
    assert (
        client.post(path, json={**body, "goal_acceptance": {"status": "PASS"}}).status_code == 422
    )
    assert table_snapshot(store) == before
    view = client.get("/api/runs/" + rid).json()
    assert (
        view["status"] == "WAITING_APPROVAL"
        and view["result"] is None
        and not view["known_effects"]
    )


def context_with_target(env):
    value, session, rid, sent, worker, *_ = prepared(env)
    store, settings, client, user, other, pid, *_ = value
    target_resource = client.post(
        "/api/projects/" + pid + "/resources",
        json={
            "name": "unseen.csv",
            "format": "csv",
            "content": "amount,quantity,bad\n30,6,x\n50,9,y\n",
        },
    ).json()["id"]
    target = client.post(
        "/api/projects/" + pid + "/apps/csv-preview",
        json={"name": "existing target", "resource_id": target_resource, "goal": "new CSV"},
    ).json()["id"]
    original = client.get("/api/runs/" + rid).json()
    return (value, session, rid, target, target_resource, original, sent), worker


def test_accepted_source_reuses_candidate_new_input_cold_result_version_bad_input(env):
    from test_internal_lifecycle import create, release
    from test_persistent_app_runs import enqueue, worker

    from sim2act.db import internal_instance_data

    context, _ = context_with_target(env)
    value, _, rid, _, _, original, sent = context
    opt, body = accepted(context)
    assert opt["whole_task_accepted"] is True
    assert opt["proof"]["kind"] == "accepted_fixed_natural_goal.v1"
    made = value[2].post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    assert (
        made["whole_task_accepted"] is True
        and made["state"] == "CANDIDATE_ONLY"
        and not made["publishable"]
    )
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    inst = create(env, rel)
    run = enqueue(env, inst, rel, column="quantity")
    cold = Store(env[1].database_url, test_only=True)
    try:
        assert worker(env, cold).once()
        view = cold.inspect(env[3], run["run_id"])
        assert (
            view["status"] == "SUCCEEDED"
            and view["result"]["sum"] == "15"
            and view["result_version"] == 1
        )
        with cold.tx() as c:
            before = [dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
        for index, column in enumerate(["missing", "bad"]):
            failed = enqueue(env, inst, rel, column=column, key="bad-" + str(index))
            assert worker(env, cold).once()
            assert cold.inspect(env[3], failed["run_id"])["status"] == "FAILED"
        with cold.tx() as c:
            assert before == [dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
    finally:
        cold.engine.dispose()
    assert value[2].get("/api/runs/" + rid).json() == original and len(sent) == 1


@pytest.mark.parametrize("change", ["partial", "missing", "report_type", "spec", "source_grant"])
def test_whole_source_invalidations_reject_read_cache_candidate_and_new_run(env, change):
    from sim2act.db import grants

    context, _ = context_with_target(env)
    value, _, rid, *_ = context
    store, _, client, *_ = value
    _, body = accepted(context)
    made = client.post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    with store.tx() as c:
        if change == "partial":
            c.execute(update(runs).where(runs.c.id == rid).values(status="PARTIAL"))
        elif change == "source_grant":
            c.execute(update(grants).where(grants.c.resource_id == value[6]).values(revoked=True))
        elif change == "missing":
            op = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one()
            c.execute(
                update(operations).where(operations.c.id == op["id"]).values(status="UNKNOWN")
            )
        elif change == "report_type":
            row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
            result = copy.deepcopy(row["result"])
            result["task_acceptance"]["whole_task_accepted"] = 1
            c.execute(update(runs).where(runs.c.id == rid).values(result=result))
        else:
            row = (
                c.execute(select(run_contracts).where(run_contracts.c.run_id == rid))
                .mappings()
                .one()
            )
            spec = copy.deepcopy(row["snapshot"])
            spec["natural_planning"]["goal_acceptance"]["check"] = "csv.complete_preview.v1"
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == rid)
                .values(snapshot=spec, fingerprint=fingerprint(spec))
            )
    before = table_snapshot(store)
    assert client.get("/api/apps/" + made["id"]).status_code in {400, 403, 409}
    assert client.post("/api/runs/" + rid + "/receipt-candidates", json=body).status_code in {
        400,
        403,
        409,
    }
    assert client.post(
        "/api/apps/" + made["id"] + "/previews",
        json={"input": {"column": "quantity"}, "request_key": "invalid"},
    ).status_code in {400, 403, 409}
    assert table_snapshot(store) == before


def test_legacy_partial_finish_cannot_be_upgraded_to_success(env):
    from test_natural_receipt_candidate import prepare

    context = prepare(env)
    value, _, rid, _, _, original, *_ = context
    store, settings, *_ = value
    with store.tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(status="RUNNING", lease_until=time.time() + 30)
        )
    with pytest.raises(DomainError):
        Worker(store, settings).finish(
            rid, row["fence"], "SUCCEEDED", result=original["result"], verify_goal_source=True
        )
    with store.tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "RUNNING"


def test_old_partial_status_only_upgrade_is_rejected_by_cold_inspection(env):
    from test_natural_receipt_candidate import prepare

    context = prepare(env)
    value, _, rid, *_ = context
    store, _, client, *_ = value
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="SUCCEEDED"))
    before = table_snapshot(store)
    assert client.get("/api/runs/" + rid).status_code == 400
    assert client.get("/api/runs/" + rid + "/receipt-candidate-options").status_code == 400
    assert table_snapshot(store) == before


def test_ordinary_page_prospective_contract_to_candidate_cold_wrong_input(env, tmp_path):
    import json
    import socket
    import subprocess
    import threading

    import uvicorn

    from sim2act.api import create_app
    from sim2act.db import grants, internal_approvals, internal_releases

    value = setup(env)
    store, settings, client, user, other, pid, resource, cards = value
    session, _ = approved(value)
    new_resource = client.post(
        "/api/projects/" + pid + "/resources",
        json={
            "name": "unseen.csv",
            "format": "csv",
            "content": "amount,quantity,bad\n30,6,x\n50,9,y\n",
        },
    ).json()["id"]
    target = client.post(
        "/api/projects/" + pid + "/apps/csv-preview",
        json={"name": "existing target", "resource_id": new_resource, "goal": "new CSV"},
    ).json()["id"]
    sent = []

    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))

    app = create_app(store, settings)

    @app.post("/test-only-fixed-worker")
    def work():
        assert store.test_only and settings.mode == "mock"
        assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
        return {"offline_test": True}

    @app.post("/test-only-fixed-revoke")
    def revoke():
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
        return {"offline_test": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "session": session["id"],
                "card": cards["sum_quantity_z"]["id"],
                "target": target,
            }
        )
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < end
            time.sleep(0.01)
        p = subprocess.run(
            ["node", "tests/fixed_goal_acceptance_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(p.stdout + p.stderr)
        assert p.returncode == 0, p.stdout + p.stderr
        assert (
            json.loads((tmp_path / "results.json").read_text())["status"] == "PASS"
            and len(sent) == 1
        )
        with store.tx() as c:
            assert (
                not c.execute(select(internal_approvals)).first()
                and not c.execute(select(internal_releases)).first()
            )
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
