"""Receipt-only bridge keeps PARTIAL honest and reuses existing CSV candidate runner."""

import copy

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_natural_activation_flow import approved, confirmation, setup, submit, wire
from test_natural_goal_planning import response

from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    fingerprint,
    grants,
    meta,
    natural_activations,
    operations,
    resources,
    runs,
    task_extractions,
)
from sim2act.worker import Worker


def prepare(env, kind="sum_quantity_z"):
    value = setup(env)
    store, settings, client, user, other, pid, resource, cards = value
    session, _ = approved(value)
    r = submit(value, session, kind).json()["run_id"]
    sent = []

    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value, kind)))

    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    assert (
        client.post(
            "/api/runs/" + r + "/confirm-natural-plan", json=confirmation(client, r)
        ).status_code
        == 200
    )
    assert worker.once()
    original = client.get("/api/runs/" + r).json()
    assert original["status"] == "PARTIAL" and not original["result"]["candidate_generated"]
    target_resource = client.post(
        f"/api/projects/{pid}/resources",
        json={
            "name": "unseen.csv",
            "format": "csv",
            "content": "amount,quantity,bad\n30,6,x\n50,9,y\n",
        },
    ).json()["id"]
    target = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={
            "name": "existing authorized target",
            "resource_id": target_resource,
            "goal": "new CSV",
        },
    ).json()["id"]
    return value, session, r, target, target_resource, original, sent


def table_snapshot(store):
    with store.tx() as c:
        return {
            t.name: [dict(r) for r in c.execute(select(t)).mappings()] for t in meta.sorted_tables
        }


def accepted(context):
    value, _, rid, target, *_ = context
    client = value[2]
    opt = client.get("/api/runs/" + rid + "/receipt-candidate-options")
    assert opt.status_code == 200, opt.text
    opt = opt.json()
    t = next(t for t in opt["targets"] if t["id"] == target)
    body = {
        "expected_proof_fingerprint": opt["source_proof_fingerprint"],
        "target_app_id": target,
        "expected_target_draft_fingerprint": t["fingerprint"],
        "name": "receipt candidate",
        "request_key": "extract-once",
    }
    return opt, body


def test_new_column_cold_store_wrong_inputs_and_no_whole_task_promotion(env):
    context = prepare(env)
    value, _, rid, _, target_resource, original, sent = context
    store, settings, client, user, *_ = value
    before = table_snapshot(store)
    opt, body = accepted(context)
    assert table_snapshot(store) == before
    made = client.post("/api/runs/" + rid + "/receipt-candidates", json=body)
    assert made.status_code == 201, made.text
    made = made.json()
    assert made["state"] == "CANDIDATE_ONLY" and not made["whole_task_accepted"]
    assert made["source_run_status"] == "PARTIAL" and not made["publishable"]
    after = table_snapshot(store)
    for table in before:
        if table not in {"app_drafts", "task_extractions"}:
            assert before[table] == after[table], table
    assert len(after["app_drafts"]) == len(before["app_drafts"]) + 1
    assert len(after["task_extractions"]) == len(before["task_extractions"]) + 1
    assert client.get("/api/runs/" + rid).json() == original
    again = client.post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    assert again["id"] == made["id"] and again["cached"] and table_snapshot(store) == after
    assert (
        client.post(
            "/api/runs/" + rid + "/receipt-candidates", json={**body, "name": "changed"}
        ).status_code
        == 409
    )
    cold = Store(settings.database_url, test_only=True)
    try:
        with TestClient(create_app(cold, settings)) as cc:
            cc.headers["Authorization"] = "Bearer synthetic-test-A"
            draft = cc.get("/api/apps/" + made["id"]).json()
            proof = draft["candidate"]["task_proof"]["proof"]
            assert proof["stable_logic"]["tool_ref"] == "data.aggregate_csv"
            assert (
                proof["parameter_scope"]["runtime"] == ["column"]
                and not proof["whole_task_accepted"]
            )
            preview = cc.post(
                "/api/apps/" + made["id"] + "/previews",
                json={"input": {"column": "quantity"}, "request_key": "new-input"},
            ).json()
            assert preview["status"] == "SUCCEEDED" and preview["output"]["sum"] == "15"
            assert (
                preview["output"]["resource_id"] == target_resource
                and preview["output"]["sum"] != "19"
            )
            for index, bad in enumerate(
                [
                    {"column": "missing"},
                    {"column": "bad"},
                    {"column": ""},
                    {"column": "quantity", "resource_id": target_resource},
                ]
            ):
                failed = cc.post(
                    "/api/apps/" + made["id"] + "/previews",
                    json={"input": bad, "request_key": "bad-" + str(index)},
                ).json()
                assert failed["status"] == "FAILED" and failed["output"] is None
            assert cc.get("/api/apps/" + made["id"]).status_code == 200
    finally:
        cold.engine.dispose()
    assert len(sent) == 1 and client.get("/api/runs/" + rid).json() == original


@pytest.mark.parametrize(
    "change",
    [
        "FAILED",
        "UNKNOWN",
        "SUCCEEDED",
        "cancel",
        "receipt",
        "material",
        "scope",
        "revoke",
        "source_grant",
        "target_grant",
        "candidate",
        "marker",
        "target_version",
    ],
)
def test_invalidated_source_or_target_denies_cached_read_and_execution_without_writes(env, change):
    context = prepare(env)
    value, session, rid, target, target_resource, _, _ = context
    store, _, client, user, *_ = value
    _, body = accepted(context)
    made = client.post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    with store.tx() as c:
        if change in {"FAILED", "UNKNOWN", "SUCCEEDED"}:
            c.execute(update(runs).where(runs.c.id == rid).values(status=change))
        elif change == "cancel":
            c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
        elif change == "receipt":
            op = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one()
            v = copy.deepcopy(op["receipt"])
            v["data"]["sum"] = "999"
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=v))
        elif change == "material":
            c.execute(
                update(resources)
                .where(resources.c.id == value[6])
                .values(content="item,quantity_z\nx,999\n", hash="0" * 64)
            )
        elif change in {"scope", "revoke"}:
            row = (
                c.execute(
                    select(natural_activations).where(natural_activations.c.id == session["id"])
                )
                .mappings()
                .one()
            )
            if change == "scope":
                v = copy.deepcopy(row["scope"])
                v["caps"]["rpm"] = 30
                c.execute(
                    update(natural_activations)
                    .where(natural_activations.c.id == session["id"])
                    .values(scope=v)
                )
            else:
                c.execute(
                    update(natural_activations)
                    .where(natural_activations.c.id == session["id"])
                    .values(status="REVOKED")
                )
        elif change.endswith("grant"):
            resource = value[6] if change == "source_grant" else target_resource
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
        elif change in {"candidate", "target_version"}:
            aid = made["id"] if change == "candidate" else target
            row = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
            v = copy.deepcopy(row["candidate"])
            v["goal"]["goal"] = "mutated" if isinstance(v["goal"], dict) else v["goal"]
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == aid)
                .values(candidate=v, fingerprint=fingerprint(v))
            )
        else:
            row = (
                c.execute(select(task_extractions).where(task_extractions.c.app_id == made["id"]))
                .mappings()
                .one()
            )
            v = copy.deepcopy(row["snapshot"])
            v["kind"] = "registered_csv_source.v1"
            c.execute(
                update(task_extractions)
                .where(task_extractions.c.app_id == made["id"])
                .values(snapshot=v)
            )
    before = table_snapshot(store)
    assert client.get("/api/apps/" + made["id"]).status_code in {400, 403, 409}
    assert client.post(
        "/api/apps/" + made["id"] + "/previews",
        json={"input": {"column": "quantity"}, "request_key": "after-invalid"},
    ).status_code in {400, 403, 409}
    assert client.post("/api/runs/" + rid + "/receipt-candidates", json=body).status_code in {
        400,
        403,
        409,
    }
    assert table_snapshot(store) == before


def test_preview_goal_foreign_owner_project_versions_and_extra_fields_are_rejected(env):
    context = prepare(env)
    value, _, rid, *_ = context
    store, _, client, user, other, pid, *_ = value
    _, body = accepted(context)
    before = table_snapshot(store)
    assert (
        client.post(
            "/api/runs/" + rid + "/receipt-candidates", json={**body, "executor": {"kind": "code"}}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/runs/" + rid + "/receipt-candidates",
            json={**body, "expected_proof_fingerprint": "0" * 64},
        ).status_code
        == 409
    )
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get("/api/runs/" + rid + "/receipt-candidate-options").status_code == 403
    assert client.post("/api/runs/" + rid + "/receipt-candidates", json=body).status_code == 403
    assert table_snapshot(store) == before


def test_fixed_preview_goal_has_no_csv_extraction(env):
    context = prepare(env, "read_preview")
    value, _, rid, *_ = context
    before = table_snapshot(value[0])
    assert value[2].get("/api/runs/" + rid + "/receipt-candidate-options").status_code == 400
    assert table_snapshot(value[0]) == before


def test_existing_durable_candidate_runner_cold_new_result_and_bad_input(env):
    from test_internal_lifecycle import create, release
    from test_persistent_app_runs import enqueue, worker

    from sim2act.db import internal_instance_data

    context = prepare(env)
    value, _, rid, _, _, original, _ = context
    _, body = accepted(context)
    made = value[2].post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    inst = create(env, rel)
    accepted_run = enqueue(env, inst, rel, column="quantity")
    cold = Store(env[1].database_url, test_only=True)
    try:
        assert worker(env, cold).once()
        final = cold.inspect(env[3], accepted_run["run_id"])
        assert final["status"] == "SUCCEEDED" and final["result"]["sum"] == "15"
        assert final["result_version"] == 1 and accepted_run["run_id"] != rid
        with cold.tx() as c:
            before = [dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
        bad = enqueue(env, inst, rel, key="bad-derived-input", column="bad")
        assert worker(env, cold).once()
        assert cold.inspect(env[3], bad["run_id"])["status"] == "FAILED"
        with cold.tx() as c:
            assert before == [dict(r) for r in c.execute(select(internal_instance_data)).mappings()]
    finally:
        cold.engine.dispose()
    assert value[2].get("/api/runs/" + rid).json() == original


def test_same_owner_foreign_project_target_rejected_zero_writes(env):
    context = prepare(env)
    value, _, rid, *_ = context
    store, _, client, user, *_ = value
    _, body = accepted(context)
    other = store.project(user, "different owned project")
    resource = client.post(
        "/api/projects/" + other + "/resources",
        json={"name": "other.csv", "format": "csv", "content": "quantity\n100\n"},
    ).json()["id"]
    target = client.post(
        "/api/projects/" + other + "/apps/csv-preview",
        json={"name": "foreign target", "resource_id": resource, "goal": "other"},
    ).json()
    before = table_snapshot(store)
    denied = client.post(
        "/api/runs/" + rid + "/receipt-candidates",
        json={
            **body,
            "target_app_id": target["id"],
            "expected_target_draft_fingerprint": client.get("/api/apps/" + target["id"]).json()[
                "fingerprint"
            ],
        },
    )
    assert denied.status_code == 403
    assert table_snapshot(store) == before


@pytest.mark.parametrize("fake", ["lost", "wrong_id", "wrong_type"])
def test_ordinary_page_actual_receipt_extraction_new_input_cold_and_revocation(env, tmp_path, fake):
    import json
    import socket
    import subprocess
    import threading
    import time

    import uvicorn

    context = prepare(env)
    value, session, rid, target, _, original, sent = context
    store, settings, client, user, *_ = value
    app = create_app(store, settings)

    @app.post("/test-only-receipt-revoke")
    def revoke():
        assert store.test_only and settings.mode == "mock"
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == value[6]).values(revoked=True))
        return {"offline_test": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    info = {
        "base": f"http://127.0.0.1:{port}",
        "project": value[5],
        "run": rid,
        "target": target,
        "fake": fake,
    }
    (tmp_path / "info.json").write_text(json.dumps(info))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < end
            time.sleep(0.01)
        p = subprocess.run(
            ["node", "tests/natural_receipt_candidate_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(p.stdout + p.stderr)
        assert p.returncode == 0, p.stdout + p.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS"
        assert len(sent) == 1
        with store.tx() as c:
            source_run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
            assert source_run["status"] == "PARTIAL" and source_run["result"] == original["result"]
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()


def test_coherent_same_value_wrong_type_proof_is_not_a_valid_candidate(env):
    context = prepare(env)
    value, _, rid, *_ = context
    store, _, client, *_ = value
    _, body = accepted(context)
    made = client.post("/api/runs/" + rid + "/receipt-candidates", json=body).json()
    with store.tx() as c:
        draft = c.execute(select(app_drafts).where(app_drafts.c.id == made["id"])).mappings().one()
        marker = (
            c.execute(select(task_extractions).where(task_extractions.c.app_id == made["id"]))
            .mappings()
            .one()
        )
        candidate = copy.deepcopy(draft["candidate"])
        snap = copy.deepcopy(marker["snapshot"])
        candidate["task_proof"]["proof"]["whole_task_accepted"] = 0
        candidate["task_proof"]["proof"]["model_requests"] = False
        snap["proof"] = copy.deepcopy(candidate["task_proof"]["proof"])
        candidate["task_proof"]["proof_fingerprint"] = fingerprint(snap["proof"])
        fp = fingerprint(candidate)
        snap["candidate_fingerprint"] = fp
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == made["id"])
            .values(candidate=candidate, fingerprint=fp)
        )
        c.execute(
            update(task_extractions)
            .where(task_extractions.c.app_id == made["id"])
            .values(snapshot=snap)
        )
    before = table_snapshot(store)
    assert client.get("/api/apps/" + made["id"]).status_code == 409
    assert client.post("/api/runs/" + rid + "/receipt-candidates", json=body).status_code == 409
    assert table_snapshot(store) == before
