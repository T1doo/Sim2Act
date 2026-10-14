"""Actual accepted project CHECK controls, Worker in-flight accounting and cold reads."""

import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from test_natural_spec_apps import transport
from test_project_account_close import check, close, one
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import project_natural_revalidation as project
from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    grants,
    internal_instance_data,
    operations,
)
from sim2act.worker import Worker


def accepted(env):
    data, aid, release, inst, _, base, _, plan = one(env, key="cancel-original")
    reply = check(data[2], base, plan, aid)
    assert reply.status_code == 202, reply.text
    started = reply.json()
    path = base + f"/plans/{plan['request_key']}/applications/{aid}"
    command = (
        f"/api/internal/instances/{started['check_instance_id']}/runs/{started['run_id']}/commands"
    )
    return data, aid, release, inst, base, plan, started, path, command


def status(client, path, metadata=False):
    reply = client.get(path + ("/run-control" if metadata else "/run-status"))
    assert reply.status_code == 200, reply.text
    assert reply.headers["cache-control"] == "no-store"
    value = reply.json()
    assert value["control_fingerprint"] == project.fingerprint(
        {k: v for k, v in value.items() if k != "control_fingerprint"}
    )
    return value


def original_objects(store, check_iid):
    rows = snapshot(store)
    return {
        k: [r for r in rows[k] if k != "internal_instances" or r["id"] != check_iid]
        for k in ["app_drafts", "internal_instances", "internal_releases", "delivery_graph_locks"]
    }


def test_public_cancel_during_real_model_return_stops_next_node_and_preserves_usage(env, tmp_path):
    data, _, _, inst, base, plan, started, path, command = accepted(env)
    saved = original_objects(data[0], started["check_instance_id"])
    sent = []
    captures = []

    def cancel_inflight(raw, payload):
        before = status(data[2], path)
        assert before["run_status"] == "RUNNING" and not before["effect_known"]
        reply = data[2].post(command, json={"command": "cancel", "version": before["run_version"]})
        assert reply.status_code == 200 and reply.json()["status"] == "RECONCILING", reply.text
        during = status(data[2], path)
        assert during["cancel_intent"] and not during["effect_known"]
        assert (
            during["run_id"] == started["run_id"]
            and during["check_instance_id"] == started["check_instance_id"]
        )
        captures.extend([before, during])

    worker = Worker(
        data[0], data[1], goal_planner_transport=transport(sent, mutate=cancel_inflight)
    )
    assert worker.once()
    final = status(data[2], path)
    assert final["run_status"] == "CANCELLED" and final["cancel_intent"] and final["effect_known"]
    assert len(sent) == 1 and final["executed_model_requests"] == 1 and final["known_effects"] == []
    assert len(final["model_usage"]) == 1 and final["model_usage"][0]["status"] == "REJECTED_KNOWN"
    assert (
        final["model_usage"][0]["usage"]["status"] == "known"
        and final["model_usage"][0]["reserved_tokens"] > 0
    )
    assert not worker.once() and len(sent) == 1
    assert original_objects(data[0], started["check_instance_id"]) == saved
    with data[0].tx() as c:
        assert not c.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.instance_id.in_([inst["id"], started["check_instance_id"]])
            )
        ).first()
        assert not c.execute(
            select(operations).where(
                operations.c.run_id == started["run_id"], operations.c.tool_ref == natural.SAVE
            )
        ).first()
        assert c.execute(
            select(attempts.c.response).where(attempts.c.run_id == started["run_id"])
        ).scalar_one()["received_raw"]
    assert close(data[2], base, plan).status_code == 409
    assert (
        "project_source"
        in data[2].get("/api/internal/instances/" + inst["id"]).json()["switch_policy"]["roles"]
    )
    cold = Store(data[1].database_url, test_only=True)
    with TestClient(create_app(cold, data[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        before = snapshot(cold)
        assert status(client, path) == final
        assert snapshot(cold) == before
        assert (
            client.post(
                command, json={"command": "cancel", "version": captures[0]["run_version"]}
            ).status_code
            == 409
        )
    cold.engine.dispose()
    (tmp_path / "inflight-cancellation.json").write_text(json.dumps(captures + [final], indent=2))


def test_unknown_model_cancel_retains_reconciling_and_never_resends(env, tmp_path):
    data, _, _, _, base, plan, started, path, command = accepted(env)
    sent = []

    def unknown(request):
        sent.append(request.content)
        raise httpx.ReadTimeout("synthetic in-flight reply unknown")

    worker = Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(unknown))
    assert worker.once()
    before = status(data[2], path)
    assert before["run_status"] == "WAITING_RESOURCE" and not before["effect_known"]
    reply = data[2].post(command, json={"command": "cancel", "version": before["run_version"]})
    assert reply.status_code == 200 and reply.json()["status"] == "RECONCILING", reply.text
    final = status(data[2], path)
    assert (
        final["cancel_intent"]
        and final["run_status"] == "RECONCILING"
        and not final["effect_known"]
    )
    assert (
        final["model_usage"] == before["model_usage"]
        and final["unresolved_operations"] == before["unresolved_operations"]
    )
    assert (
        final["model_usage"][0]["status"] == "STARTED"
        and final["model_usage"][0]["usage"]["status"] == "unknown"
    )
    assert not worker.once() and len(sent) == 1 and close(data[2], base, plan).status_code == 409
    before_db = snapshot(data[0])
    assert status(data[2], path) == final
    assert snapshot(data[0]) == before_db
    (tmp_path / "unknown-cancellation.json").write_text(json.dumps([before, final], indent=2))


def test_revoked_owner_can_stop_and_cold_read_only_public_exact_binding(env, monkeypatch):
    data, _, _, _, base, plan, started, path, command = accepted(env)
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
    assert data[2].get(path + "/run-status").status_code == 403
    own_pair = project.pair

    def public_only(*args, **kwargs):
        assert args[3] != project.PLAN, "private PLAN body read during owner stop"
        return own_pair(*args, **kwargs)

    monkeypatch.setattr(project, "pair", public_only)
    cold = Store(data[1].database_url, test_only=True)
    with TestClient(create_app(cold, data[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        before = snapshot(cold)
        v = status(client, path, True)
        assert v["content_access"] is False and "effect_known" not in v and "model_usage" not in v
        index = client.get(base + f"/plans/{plan['request_key']}/run-controls")
        assert index.status_code == 200 and index.json()["applications"][0]["accepted_check"]
        assert snapshot(cold) == before
        reply = client.post(command, json={"command": "cancel", "version": v["run_version"]})
        assert reply.status_code == 200 and reply.json()["status"] == "CANCELLED", reply.text
        after = status(client, path, True)
        assert after["cancel_intent"] and after["run_status"] == "CANCELLED"
        assert (
            after["run_id"] == started["run_id"]
            and after["plan_fingerprint"] == plan["plan_fingerprint"]
        )
        client.headers["Authorization"] = "Bearer synthetic-test-B"
        assert client.get(path + "/run-control").status_code == 403
        assert (
            client.post(
                command, json={"command": "cancel", "version": after["run_version"]}
            ).status_code
            == 403
        )
    cold.engine.dispose()


@pytest.mark.parametrize("fault", ["start_seal", "job_seal", "project_reference"])
def test_changed_project_control_binding_never_accepts_stop(env, fault):
    data, _, _, _, _, _, started, path, command = accepted(env)
    version = status(data[2], path, True)["run_version"]
    with data[0].tx() as c:
        if fault == "project_reference":
            from sim2act.db import internal_run_bindings

            row = (
                c.execute(
                    select(internal_run_bindings).where(
                        internal_run_bindings.c.run_id == started["run_id"]
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(row["snapshot"])
            value["project_check"]["plan_key"] = "foreign-key"
            c.execute(
                update(internal_run_bindings)
                .where(internal_run_bindings.c.run_id == started["run_id"])
                .values(snapshot=value)
            )
        else:
            kind = project.START + "_seal" if fault == "start_seal" else project.JOB + "_seal"
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == kind))
    before = snapshot(data[0])
    assert data[2].get(path + "/run-control").status_code == 409
    assert data[2].post(command, json={"command": "cancel", "version": version}).status_code == 409
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("winner", ["cancel", "save"])
def test_real_worker_final_save_boundary_respects_winner_and_keeps_accounting(
    env, monkeypatch, tmp_path, winner
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sim2act import pa_spec_apps as spec

    data, _, _, _, base, plan, started, path, command = accepted(env)
    ready = Event()
    release = Event()
    sent = []
    advance = spec.advance

    def final_boundary(worker, run, **kwargs):
        with data[0].tx() as c:
            count = len(
                c.execute(
                    select(operations.c.id).where(
                        operations.c.run_id == started["run_id"], operations.c.status == "VERIFIED"
                    )
                ).all()
            )
        if run["id"] == started["run_id"] and count == 5:
            ready.set()
            assert release.wait(20), "owned SAVE boundary was not released"
        return advance(worker, run, **kwargs)

    monkeypatch.setattr(spec, "advance", final_boundary)
    worker = Worker(data[0], data[1], goal_planner_transport=transport(sent))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker.once)
        try:
            assert ready.wait(180), "actual worker never reached final SAVE boundary"
            control = status(data[2], path, True)
            assert control["run_status"] == "RUNNING"
            if winner == "cancel":
                reply = data[2].post(
                    command, json={"command": "cancel", "version": control["run_version"]}
                )
                assert reply.status_code == 200 and reply.json()["status"] == "CANCEL_REQUESTED", (
                    reply.text
                )
            release.set()
            assert future.result(timeout=90)
        finally:
            release.set()
    final = status(data[2], path)
    assert len(sent) == 2 and len(final["model_usage"]) == 2
    assert all(
        x["usage"]["status"] == "known" and x["reserved_tokens"] > 0 for x in final["model_usage"]
    )
    if winner == "cancel":
        assert (
            final["run_status"] == "CANCELLED"
            and final["cancel_intent"]
            and final["known_effects"] == []
        )
    else:
        assert (
            final["run_status"] == "SUCCEEDED"
            and not final["cancel_intent"]
            and len(final["known_effects"]) == 1
        )
        before = snapshot(data[0])
        assert (
            data[2]
            .post(command, json={"command": "cancel", "version": control["run_version"]})
            .status_code
            == 409
        )
        assert snapshot(data[0]) == before and status(data[2], path) == final
    assert close(data[2], base, plan).status_code == 409 and not worker.once()
    (tmp_path / "final-save-boundary.json").write_text(
        json.dumps({"winner": winner, "before": control, "after": final}, indent=2)
    )


def test_two_store_cancel_version_competition_accepts_once(env, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    data, _, _, _, _, _, _, path, command = accepted(env)
    version = status(data[2], path, True)["run_version"]
    barrier = Barrier(2)

    def stop():
        store = Store(data[1].database_url, test_only=True)
        try:
            with TestClient(create_app(store, data[1])) as client:
                client.headers["Authorization"] = "Bearer synthetic-test-A"
                barrier.wait(timeout=20)
                reply = client.post(command, json={"command": "cancel", "version": version})
                return reply.status_code, reply.json()
        finally:
            store.engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(stop)
        second = pool.submit(stop)
        results = [first.result(timeout=60), second.result(timeout=60)]
    assert sorted(x[0] for x in results) == [200, 409], results
    final = status(data[2], path, True)
    assert (
        final["run_status"] == "CANCELLED"
        and final["cancel_intent"]
        and final["run_version"] == version + 1
    )
    (tmp_path / "cancel-version-race.json").write_text(
        json.dumps({"results": results, "after": final}, indent=2)
    )


def test_resealed_project_markers_cannot_rebind_original_run_to_another_key(env):
    from sim2act.db import internal_run_bindings
    from sim2act.text_logic_reuse import remember

    data, aid, _, _, base, plan, started, path, command = accepted(env)
    version = status(data[2], path, True)["run_version"]
    options = data[2].get(base + "/options").json()
    body = copy.deepcopy(plan["request"])
    body["request_key"] = "another-explicit-account"
    body["expected_options_fingerprint"] = options["options_fingerprint"]
    for selection in body["selections"]:
        selection["preview_key"] = None
        selection["expected_preview_fingerprint"] = None
    reply = data[2].post(base + "/plans", json=body)
    assert reply.status_code == 201, reply.text
    other = reply.json()
    with data[0].tx() as c:
        start_body, start_value = project.pair(
            c, data[3], data[4], project.START, plan["request_key"] + ":" + aid, project.Start
        )
        c.execute(
            delete(delivery_graph_requests).where(
                delivery_graph_requests.c.principal_id == data[3],
                delivery_graph_requests.c.kind.in_(
                    [project.START, project.START + "_seal", project.JOB, project.JOB + "_seal"]
                ),
            )
        )
        reference = project.ref(data[4], other["request_key"], other, aid)
        remember(
            c,
            data[3],
            started["run_id"],
            project.JOB,
            "accepted",
            reference,
            reference.model_dump(),
        )
        start_body = project.Start(
            expected_plan_fingerprint=other["plan_fingerprint"], consent=project.CONSENT
        )
        forged = {
            **start_value,
            "plan_key": other["request_key"],
            "plan_fingerprint": other["plan_fingerprint"],
            "role": "REVALIDATE_UNCHANGED",
        }
        remember(
            c, data[3], data[4], project.START, other["request_key"] + ":" + aid, start_body, forged
        )
        binding = (
            c.execute(
                select(internal_run_bindings).where(
                    internal_run_bindings.c.run_id == started["run_id"]
                )
            )
            .mappings()
            .one()
        )
        changed = copy.deepcopy(binding["snapshot"])
        changed["project_check"] = reference.model_dump()
        c.execute(
            update(internal_run_bindings)
            .where(internal_run_bindings.c.run_id == started["run_id"])
            .values(snapshot=changed)
        )
    before = snapshot(data[0])
    # Every public project pair and scalar reference agree with the other genuine PLAN.
    # The independent originally accepted CHECK id still belongs to the original key.
    other_path = base + f"/plans/{other['request_key']}/applications/{aid}/run-control"
    assert data[2].get(other_path).status_code == 409
    assert data[2].post(command, json={"command": "cancel", "version": version}).status_code == 409
    assert snapshot(data[0]) == before
